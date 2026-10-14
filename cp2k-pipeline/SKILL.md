---
name: cp2k-pipeline
description: Pipeline, regras e fatos verificados para cálculos CP2K (GPW/Quickstep, PBE, DZVP-MOLOPT) do usuário em access (cp2k/2026.1, MPICH) e coaraci (2025.1 psmp / 2026.2 ssmp) — convergência CUTOFF/REL_CUTOFF (método 2D), k-mesh, CELL_OPT, bandas, PDOS, slabs/energia de superfície/Wulff/forma de crescimento, híbridos RI-HFXk (HSE06/PBE0, bloqueio de memória), migração VASP→CP2K. Use SEMPRE que o usuário for iniciar, retomar ou depurar algo em CP2K (.inp, .out, .restart, cp2k.psmp/ssmp, mpiexec/srun, &QS, &KPOINTS, &OT, BAND_STRUCTURE, PDOS, work_cp2k, ZrO2, TiO2), ou perguntar "faz no CP2K o que fazíamos no VASP" — mesmo sem dizer "CP2K".
---

# Pipeline CP2K

Pipeline reconstruído e versionado em `~/work_cp2k` (= `git@github.com:robertoramosjr/cp2k_scripts.git`, `main`; só código, dados nunca). Verificado contra a documentação oficial e contra builds reais (2025.1, 2026.1, 2026.2). Os detalhes completos estão em `references/` — este arquivo é o que se precisa antes de tocar em qualquer coisa.

**Por que existe:** o pipeline foi reescrito duas vezes porque o desenho "VASP traduzido" estava inválido (PDOS com k-points não existe, `ADDED_MOS` 9× maior que o oficial, CELL_OPT a 100 bar por default). Toda decisão aqui tem uma prova (manual, schema `--xml` ou run real). Não re-derivar nem re-propor opções já fechadas (HFX com k-points, §5).

## 0. Regras duras

1. **Chat em português; scripts/comentários/argparse em inglês.**
2. **`cp2k --check` prova só sintaxe.** Nunca dizer "funciona" sem run real (teste curto no login com 2 ranks é aceito; senão fila de teste/`sbatch`).
3. **Reportar custo antes de submeter**; nada pesado no login node; não decidir arquitetura sozinho; avisar quando um pedido parte de premissa errada ("HSE06 = GGA, deve ser barato" é falso em Gaussianas).
4. **Sucesso = `OPTIMIZATION COMPLETED`** (GEO/CELL_OPT) ou `PROGRAM ENDED` com energia (ENERGY). Terminar não basta; `SCF run NOT converged` invalida.
5. **O CP2K *acrescenta* ao `.out` existente:** parsers/monitores leem só o último segmento `PROGRAM STARTED AT`.
6. **Conferir a linha `Total number of message passing processes`** == tarefas pedidas (srun puro roda N singletons).
7. Jobs só em FS compartilhado (`/tmp` é local ao nó); caminhos absolutos; a ferramenta Write pode dar timeout no hook → fallback `cat > f <<'EOF'` e `ls`.
8. Nunca versionar chave de API (os scripts legados tinham a do Materials Project).

## 1. VASP → CP2K (a tradução que importa)

| VASP | CP2K | Observação |
|---|---|---|
| ISIF=3 depois ISIF=2 | **um só** `RUN_TYPE CELL_OPT` (íons+célula) | a base é gaussiana (acompanha os átomos); `CELL_REF` 1.15× fixa a grade |
| ISIF=2 | `GEO_OPT` | célula fixa (slabs) |
| ENCUT | `CUTOFF` **+ `REL_CUTOFF`** (acoplados) | método 2D (§2) |
| NBANDS = NELECT | `ADDED_MOS 2–10` | 18 estourou memória |
| ICHARG=11 | SCF único + `&PRINT%BAND_STRUCTURE`/`&KPOINT_SET` | barato, igual espírito |
| DOS com k denso | **PDOS Γ-only em supercélula (OT)** | PDOS + k-points é inválido |
| PSTRESS | `EXTERNAL_PRESSURE [bar] 0` explícito | default = **100 bar** |
| HSE06 em bandas | RI-HFXk, **memória-bloqueado** | §5 |

## 2. Pipeline (scripts em `~/work_cp2k`, `core/cp2k_blocks.py` = fonte única de blocos, `--basis` obrigatório)

```
01 grid: CUTOFF e REL_CUTOFF (RUN_TYPE ENERGY, MAX_SCF 1, IGNORE_CONVERGENCE_FAILURE, PRINT_LEVEL MEDIUM, Γ)
   --phase cutoff (200/300→1000 Ry, REL 60) → --phase relcutoff (10→100 com o CUTOFF escolhido)
   critério: menor CUTOFF com o grid 1 usado e a maioria das Gaussianas nos grids grossos; ΔE < limiar meV/átomo
02 k-mesh: CELL_OPT completo por malha (--k-list | --densities), ΔE meV/átomo e ΔV % vs. malha mais densa
03 CELL_OPT de produção (CELL_REF 1.15×, STRESS_TENSOR ANALYTICAL, EXTERNAL_PRESSURE 0, BFGS ≤10 át./LBFGS >10)
04 bandas: ENERGY + BAND_STRUCTURE (kpath.prim no &CELL/&COORD; ADDED_MOS 10)
05 PDOS: supercélula, Γ, OT (--dos-interface legacy|unified)
06 slab_cut → 07 slab_opt (GEO_OPT, --vacuum, --no-dipole) → parse_surface_energy → Wulff
08 thickness_series + parse_thickness / parse_growth_shape (Winterbottom)
```
Valores medidos (ZrO2, PBE, DZVP-MOLOPT-SR-GTH q12/q6): **CUTOFF 600 / REL_CUTOFF 50 Ry** (c/t 30, m 40 no scan), k-mesh c 4×4×4, t 5×5×3, m 3×3×3, vácuo de produção 25 Å (custa só grade no GPW).

Blocos comuns: Γ-only = `&OT` (DIIS, FULL_SINGLE_INVERSE) + `&OUTER_SCF`, **sem `&KPOINTS`** (mesmo 1×1×1 aborta o OT); k ≠ Γ = `&DIAGONALIZATION` (`EPS_ADAPT 0.01`) + `&MIXING` Broyden α 0.4 (0.2 em slab) + `&SMEAR` FERMI_DIRAC 300 K + `ADDED_MOS 10`; `&QS EPS_DEFAULT 1E-12`, `EXTRAPOLATION USE_GUESS`; `NGRIDS 5`.

## 3. Lançar (access / coaraci)

- **access:** `module load cp2k/2026.1`, `export CP2K_DATA_DIR="$CP2K_DATA"`, conda `cp2k_env` (pymatgen). Lançar com **`mpiexec -n $SLURM_NTASKS -bind-to core:$OMP_NUM_THREADS`** (MPICH do toolchain; nunca `srun` puro). Padrão `-N1 --ntasks-per-node=14 --cpus-per-task=2 --mem-per-cpu=2194M`; filas short/medium/long.
- **coaraci:** nó inteiro sempre → tarefas×threads = 48. Submeter por `jobs/sbatch_coaraci.sh` (exporta `CP2K_CLUSTER=coaraci`; nunca detectar por hostname dentro do batch). 1 tarefa → `cp2k.ssmp` 2026.2 local; N tarefas → 2025.1 `psmp` com `srun --mpi=pmix` + `SRUN_CPUS_PER_TASK`. Partições `par48-x` (3 d), `teste` (30 min), `fat`. Sem `short/medium/long`; `cp2k/2025.2` default está quebrado.
- Jobs do repo: `jobs/common.sh` (env, `run_cp2k`, `is_done`, `run_dir` com restart), `job_scan_array.sh DIR|LIST_FILE`, `job_single.sh`, `job_sequential.sh LIST`. Restart-safe: reenviar o mesmo comando pula os OK.
- Retomar após `MAX_ITER`: o `.restart` guarda `MAX_ITER`/`STEP_START_VAL` — aumentar **dentro do `.restart`** (jobs imprimem `[max_iter]`). `&CELL_REF` fica aninhado em `&CELL` no restart: leitor ingênuo devolve a célula 1.15×.

## 4. Armadilhas frequentes (lista completa na spec §1)

`EXTERNAL_PRESSURE` default 100 bar · `IGNORE_CONVERGENCE_FAILURE` só no `MAX_SCF 1` · arrays: `&SCF%PRINT%RESTART OFF` (o writer `.kp` crasha com I/O concorrente) · `PDOS` 2026.1 = `&DFT%PRINT%PDOS`; 2026.2 = `&DFT%PRINT%DOS%PDOS` (cabeçalho do `.pdos` muda) · `Slab.is_polar()` e `SlabGenerator` (pymatgen) exigem oxidação/`reorient_lattice=False` · `--planes="-1,1,1;…"` (argparse come o `-`) · `SURFACE_DIPOLE_CORRECTION` aborta com pouco vácuo (slabs simétricos: `--no-dipole`) · numpy 2: `np.trapz`→`np.trapezoid` · c-ZrO2 é instável a 0 K: slabs cúbicos relaxam para tetragonal (γ calculado contra bulk cúbico subestima até ~0,37 J/m²) · estimativas de tempo/memória sempre para cima.

## 5. HFX / híbridos — **PAUSADO; não re-derivar**
RI-HFXk (HSE06/PBE0 com k-points) é bloqueado por memória (38→390 GiB/rank conforme `EPS_PGF_ORB`), `RI_FLAVOR MO` aborta com smearing, `EPS_FILTER` dá −20 %, HFX sem RI com k-points dá segfault, `MIX_CL_TRUNC` aborta com k-points. Rota prática: PBE para bandas e híbrido só em Γ/supercélula (PBE0-TC R_c 4–6 Å, supercélula ≥ 9–12 Å) ou outro código (o usuário foi para CRYSTAL). Detalhes: `references/machines-facts-hfx.md` §6.

## Mapa de referências

| Arquivo | Quando abrir |
|---|---|
| `references/pipeline-spec.md` | spec completa: achados 1.1–1.19, scripts 01–07, superfícies, HFX/PDOS |
| `references/machines-facts-hfx.md` | regras de engajamento, máquinas, fatos verificados 2025.1/2026.1/2026.2, formatos de saída, HSE06/RI-HFXk, jobs |
| `references/zro2-slabs-lessons.md` | estudo de slabs ZrO2: decisões, números, armadilhas, forma de crescimento (Winterbottom) |

## Ao fechar uma etapa
Atualizar a nota do projeto em `~/cofre/02_Memory/cp2k/<projeto>.md` e o `active_session.md`; commit+push do cofre e do repo `cp2k_scripts` (código). Fatos novos e verificados do CP2K entram em `references/machines-facts-hfx.md` deste repo de skills.
