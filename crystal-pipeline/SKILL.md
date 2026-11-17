---
name: crystal-pipeline
description: RITO OBRIGATÓRIO em CRYSTAL23 (sempre nesta ordem, igual ao vasp-pipeline - 1 STRESS com convergência de k-points = FULLOPTG (célula+íons, ISIF=3) em cada malha l = 05…50 do "Auto" do VASP, 2 escolha da malha pelo usuário, 3 FULLOPTG de produção, 4 ETOT = ATOMONLY (ISIF=2) na célula final, 5 DOS/PDOS (NEWK/DOSS, malha 3×, NPT 6001) e bandas no caminho de alta simetria Setyawan–Curtarolo (o mesmo do gen_kpath.py do VASP) via properties; rito completo para cada funcional, GGA (PBE/PBEsol) e híbrido (HSE06/PBE0/B3LYP)). Gaussianas (pob-TZVP-rev2, ECP), harpia (CRYSTAL 23.1.0.1; layout de paralelização e variáveis de ambiente medidos), grupo espacial real via spglib, manual oficial CRYSTAL23 indexado em references/ para consulta via grep. Use SEMPRE que o usuário for iniciar, retomar ou depurar algo em CRYSTAL (INPUT/d12, d3, crystal.out, fort.9, fort.34, fort.25, DOSS.DAT, BAND.DAT, OPTINFO.DAT, SCFOUT.LOG, SHRINK, TOLINTEG, FULLOPTG, ATOMONLY, NEWK, DOSS, BAND, crystalOMP, Pcrystal, properties, work_crystal), pedir bandas/DOS com funcional híbrido em sólido, ou "faz no CRYSTAL o que fazíamos no VASP/CP2K" — mesmo sem dizer "CRYSTAL".
---

# Pipeline CRYSTAL23

CRYSTAL (LCAO, Gaussianas) entrou para fazer **bandas/DOS com funcional híbrido e k-points**, o que travou nos outros códigos: no CP2K o RI-HFXk bate no muro de memória (`cp2k-pipeline` §5) e o `riper` do TURBOMOLE não tem gradiente com híbrido (teste 875, 2026-11-17). No CRYSTAL o híbrido custa mais no SCF, mas **bandas e DOS saem do `fort.9` sem custo extra de troca exata**. O VASP é a referência: o rito abaixo é o do `vasp-pipeline` traduzido, inclusive nos scripts de origem (`bash_stress_coaraci.sh`, `extract_stress_data.py`, `gen_kpath.py` do repo `robertoramosjr/VASP`, `scripts/`).

> ➡️ **MANUAL OFICIAL — consulte SEMPRE antes de adivinhar:** `references/CRYSTAL23_Manual.md` (CRYSTAL23 User's Manual, 31/10/2023; 28,9 mil linhas, 2 MB; vem no `git pull`). **Nunca ler inteiro:** `grep -n -i` e depois `sed -n 'A,Bp'`. O topo tem índice com linha: **A** = sumário (seção → página → linha), **B** = keywords do pipeline (SHRINK, TOLINTEG, FULLOPTG/ATOMONLY, FINALRUN, EXTPRESS, BAND, NEWK, DOSS, HSE06, grades...), **C** = página → linha (resolve os "see page N" do texto). O texto veio de PDF: tabelas viram `|` quebrados e palavras grudam (`thekeywordFOO`): buscar com `-i` e pedaços de palavra. Ex.: `grep -n "^- SHRINK\|^- NEWK" references/CRYSTAL23_Manual.md`. Regenerar: `references/build_crystal_manual.py`.

## 🚨 O RITO — OBRIGATÓRIO, SEMPRE NESTA ORDEM, COM CADA FUNCIONAL

> **Nomes de pasta: padrão obrigatório** `work_crystal/<material>/<tipo>_<base>_<funcional>[_OK]` (ex.: `ag2seo3/stress_pob-TZVP-rev2_b3lyp`; `cry_input.py --root <material> --name <tipo>_<base>_<funcional>`); ver `~/cofre/02_Memory/meta/nomenclatura-pastas.md`. `_OK` ao terminar.
>
> Toda estrutura nova começa pelo stress com convergência de k. Nunca pela energia, nunca pela DOS, nunca com SHRINK escolhido à mão (a falha registrada no VASP em 2026-11-09). **Rito completo para cada funcional** (geometria própria; decisão do usuário, 2026-11-17).

| # | Etapa | VASP | CRYSTAL | Fecha a etapa |
|---|---|---|---|---|
| **0** | Geometria com o grupo real | POSCAR | `cry_symm.py --verify` (spglib → `crygeo` com unidade assimétrica; o CRYSTAL confere) | `verify ... OK` |
| **1** | **STRESS + convergência de k** | ISIF=3 em `05/ … 50/` (`KPOINTS Auto`, l passo 5), job sequencial com ressubmissão | `cry_input.py --mode kconv` → `runs/<f>_stress_kconv/05 … 50`, **FULLOPTG em cada `l`**; `sbatch job_crystal.sh runs/<f>_stress_kconv` (sequencial, pula convergidas, restart, ressubmete com < 90 min) | `cry_parse.py kconv` → `dados_convergencia_final.csv` (l, malha, a b c, V, E, pasta, ΔE meV/át., ΔV %) |
| **2** | **Escolha da malha** (propor, **o usuário decide**) | idem | `l` do **platô com folga**: nem a menor nem a maior | malha registrada |
| **3** | Stress de produção | a pasta do `l` escolhido | a pasta do `l` escolhido já é o FULLOPTG convergido (`fort.34`) | `OPT END - CONVERGED` |
| **4** | **ETOT: só íons** | ISIF=2 (1.125×ENMAX) | `--mode atomopt --geom runs/<f>_stress_kconv/<l>/fort.34` (`EXTERNAL` + `ATOMONLY`) | `OPT END - CONVERGED`; energia comparável |
| **5** | **DOS + bandas** | estático (CHGCAR) → DOS malha 3×, `NEDOS=6001`; bandas `ICHARG=11` no caminho do `gen_kpath.py` | SCF na geometria da etapa 4 (`--mode sp` → `fort.9`) → `cry_kpath.py` (Setyawan–Curtarolo) → `cry_props.py` → `properties`: **BAND → NEWK → DOSS** | `bands.csv` + `bands_ticks.csv`, `DOS_raw_data.csv`, gap do caminho e da rede |

**Malha k (etapa 1):** a regra do `Auto`: `N_i = max(1, int(l·|b_i| + 0.5))`, |b_i| da **célula primitiva** sem 2π (grupo centrado → `--cell-from crystal.out|fort.34`). Malhas repetidas entre `l` vizinhos não são recalculadas (`kmesh_map.txt`; aparecem na tabela como `(= ll)`). O "repetir o ISIF=3 até o OSZICAR ter uma única linha `F=`" do VASP serve para reconstruir a base de ondas planas; no CRYSTAL a base segue os átomos e o equivalente embutido é o `FINALRUN 4` (default). No INPUT: `SHRINK IS ISP` ou `SHRINK 0 ISP` + `IS1 IS2 IS3` + `NOSYMADA` (exigido pelo manual p.125; testado com 16 operações), ISP = 2·IS1. Supercélula: dividir as subdivisões pelo fator do eixo, arredondando para cima.

**Por que a etapa 4 existe sem ENCUT:** não há stress de Pulay de base fixa, mas a **classificação das integrais (FIXINDEX) fica presa à geometria inicial** durante a otimização (manual §7.4.1): o ATOMONLY partindo do `fort.34` reclassifica tudo na célula final, e mantém o protocolo do VASP (energias de defeitos/fases sempre a célula fixa). **Não trocar base, ECP, TOLINTEG nem grade entre etapas** (o "não trocar POTCAR").

**Bandas = caminho de alta simetria, não single point.** O SCF da etapa 5 é o análogo do estático que gera o CHGCAR; as bandas são autovalores ao longo do caminho (= `ICHARG=11`), com a **mesma convenção do `gen_kpath.py`** do VASP (`pymatgen HighSymmKpath`, Setyawan–Curtarolo 2010, 40 pontos por segmento). O `gen_kpath.py` padroniza a estrutura (`POSCAR_bands`) e exige novo SCF se a célula mudar; o `cry_kpath.py` não mexe na estrutura: converte os pontos para a base recíproca primitiva do próprio CRYSTAL (matriz unimodular validada pelos átomos). Relatar **gap do caminho e da rede SCF**: no Ag2SeO3 B3LYP o VBM fica fora da malha 3×3×3 (caminho 3,845 eV × rede 3,9135 eV).

**DOS (regras do usuário herdadas do VASP, 2026-11-11):** NEWK = **3× a malha do SCF em cada eixo**, ISP = 2×IS; **NPT = 6001** (o "NEDOS"), NPOL 18; PDOS por elemento. RSH (HSE06) desliga a expansão bipolar da troca: custa 2–3× um híbrido global (manual p.138).

## 0. Regras duras

1. Chat em português; scripts/comentários/argparse em inglês.
2. **Reportar custo (núcleo-h, walltime) antes de qualquer `sbatch`**; um passo por vez; nada pesado no login (teste de segundos com 2–4 threads é aceito).
3. **Validar por texto, nunca por exit code/`sacct`:** `EEEEEEEEEE TERMINATION` + `SCF ENDED - CONVERGENCE` (+ `OPT END - CONVERGED`). Properties: `TERMINATION` e nenhum `ERROR ****` (o `properties` sai com rc 0 mesmo com erro).
4. **Limites padrão:** SCF `MAXCYCLE 1500`, OPTGEOM `MAXCYCLE 800`; OPTGEOM com **`ONELOG`** (sem ele o log vai para `SCFOUT.LOG` depois do 1º ciclo, o `crystal.out` para de crescer e o watchdog pode matar um job saudável).
5. **Grupo espacial real** (`cry_symm.py`), nunca P1: TiO2 P1 = 19 k na IBZ × 9 em P4₂/mnm. Ag2SeO3 = **P2₁/c** (24 → 6 átomos; `~/work_crystal/ag2seo3/geom/ag2seo3_P21c.crygeo`, verificado 2026-11-17).
6. **Paralelização = §2. Não inventar layout nem variáveis**: usar o `job_crystal.sh` (bloco de ambiente medido).
7. Watchdog obrigatório (`~/skills/global/job_watchdog.sh`, já no job; desde 2026-11-17 preserva o stdin, `run_watched prog < INPUT` funciona).
8. Não decidir sozinho: funcional, base, malha final, spin/ordem magnética, layout diferente do padrão.

## 1. Scripts (`scripts/`, testados em runs reais em 2026-11-17)

| Script | Faz |
|---|---|
| `cry_symm.py` *(render_env)* | POSCAR/CIF/P1/`fort.34` → `crygeo` com grupo espacial (spglib) e unidade assimétrica; `--verify` roda TESTGEOM e compara volume, composição e distâncias |
| `cry_input.py` | `runs/<nome>/INPUT` para `kconv` (padrão VASP, FULLOPTG por `l`), `fullopt`, `atomopt`, `sp`; geometria `crygeo`/`fort.34` (EXTERNAL)/POSCAR; base por arquivo (`--basis-dir basis --basis-tag pob-TZVP-rev2`, checa o Z do ECP, 247 = Ag) ou `--basisset`; `--spin/--spinlock/--levshift/--guessp/--extra3` |
| `cry_kpath.py` *(render_env)* | caminho Setyawan–Curtarolo (pymatgen) na base do CRYSTAL → `KPATH_CRYSTAL` |
| `cry_props.py` | `PROPS` (BAND → NEWK → DOSS) a partir do `crystal.out` (+ `--kpath-file`) |
| `cry_parse.py` | `check`, `kconv` (CSV estilo VASP), `opt`, `dos` (→ `DOS_raw_data.csv`), `bands` (→ `bands.csv`, `bands_ticks.csv`, VBM/CBM/gap com rótulo) |
| `job_crystal.sh` | `sbatch job_crystal.sh DIR [DIR…]` ou pasta-mãe (kconv), `--props DIR`; sequencial, pula convergidas, restart de OPTGEOM (`RESTART` + `OPTINFO.DAT` + `fort.9→fort.20`, testado), corta 20 min antes do fim e se ressubmete; `LAYOUT=omp|hybrid|mpi` |

*(render_env)* = `~/micromamba/envs/render_env/bin/python` (pymatgen 2026.9.24, spglib 2.8.0); os demais rodam no `python3` do sistema.

```bash
S=~/skills/crystal-pipeline/scripts; PY=~/micromamba/envs/render_env/bin/python
$PY $S/cry_symm.py mat.cif -o geom/mat.crygeo --verify                                          # 0
python3 $S/cry_input.py --geom geom/mat.crygeo --basis-dir basis --basis-tag pob-TZVP-rev2 \
        --func HSE06 --mode kconv --name hse_stress_kconv                                       # 1
sbatch $S/job_crystal.sh runs/hse_stress_kconv; python3 $S/cry_parse.py kconv runs/hse_stress_kconv   # 1→2
python3 $S/cry_input.py --geom runs/hse_stress_kconv/30/fort.34 ... --mode atomopt --k 6 3 4 --name hse_atomopt  # 4
python3 $S/cry_input.py --geom runs/hse_atomopt/fort.34 ... --mode sp --k 6 3 4 --name hse_sp     # 5
$PY $S/cry_kpath.py runs/hse_sp/crystal.out
python3 $S/cry_props.py --scf-out runs/hse_sp/crystal.out --what both --kpath-file runs/hse_sp/KPATH_CRYSTAL
sbatch -t 04:00:00 $S/job_crystal.sh --props runs/hse_sp; python3 $S/cry_parse.py bands runs/hse_sp; python3 $S/cry_parse.py dos runs/hse_sp
```
Detalhes, critérios, restart e spin: `references/workflow.md`.

## 2. Paralelização e ambiente na harpia (CRÍTICO; medido em 2026-11-17)

**Hardware/Slurm:** 1 nó, 2 sockets × 32 núcleos × 2 hyperthreads = **128 CPUs Slurm** (Xeon 6530P, 2 NUMA). `SelectTypeParameters=CR_CPU_MEMORY` e o Slurm entrega **núcleos inteiros como pares de hyperthreads**: **48 CPUs = 24 núcleos físicos** (job 879: cpuset `0-23,64-87`; job 866: `32-55,96-119`). QoS `harpia_48a/b`: máx. **48 CPUs e 48 GB por usuário** por partição; RAM 900 MB/CPU → `--mem=43200M`. Pedir sempre número **par** de CPUs.

**Benchmark (jobs 879 e 893; Ag2SeO3 P2₁/c, B3LYP, pob-TZVP-rev2, XXLGRID, TOLINTEG 8, k333; 48 CPUs):**

| Layout | SCF (6 ciclos) | SCF completo + 1 gradiente (FULLOPTG, 1 ponto) |
|---|---|---|
| **crystalOMP, 48 threads (2/núcleo)** | **208 s** | **667 s** |
| crystalOMP, 24 threads (1/núcleo) | 229 s | — |
| PcrystalOMP, 24 ranks × 2 threads | 226 s | 711 s |
| Pcrystal, 24 ranks | 251 s | 1094 s |
| Pcrystal, 48 ranks (HT) | 264 s | — |

**Conclusão: crystalOMP com 48 threads é o padrão** (mais rápido no SCF e no gradiente; 1 processo = menos memória que N ranks replicados). O MPI puro escala pior na troca exata (`SHELLXN`/`SHELXG`: 1094 × 667 s no gradiente). ~90 % do tempo do SCF é troca exata. Reavaliar (`LAYOUT=hybrid`) só para célula muito maior ou muitos k-pontos, com benchmark curto antes. `OMP_PLACES=cores` e `=threads` deram tempo idêntico com 48 threads (os dois põem 2 threads por núcleo). Energias idênticas entre layouts.

**Padrão (`job_crystal.sh`, `LAYOUT=omp`):** cabeçalho único `--ntasks=24 --cpus-per-task=2 --mem=43200M` (serve para os três layouts) e
```bash
module purge; module load modmat/crystal/23.1.0.1
export PATH=/home/hpc/software/openmpi/4.1.8-orca/bin:$PATH        # só para Pcrystal/PcrystalOMP
export LD_LIBRARY_PATH=/home/hpc/software/openmpi/4.1.8-orca/lib:/opt/intel/oneapi/compiler/2026.2/lib:$LD_LIBRARY_PATH
export OMP_NUM_THREADS=$SLURM_CPUS_ON_NODE        # 48 = todos os hyperthreads dos 24 núcleos
export OMP_PLACES=threads OMP_PROC_BIND=close OMP_DYNAMIC=FALSE OMP_STACKSIZE=512M MKL_NUM_THREADS=1
ulimit -s unlimited
$CRY23_ROOT/bin/Linux-ifort_i64_omp/v1.0.1/crystalOMP < INPUT > crystal.out
```
- O módulo **não** traz MPI: `Pcrystal`/`PcrystalOMP` precisam de `libmpi.so.40` → OpenMPI **4.1.8** do cluster (`/home/hpc/software/openmpi/4.1.8-orca`, com suporte a Slurm; testado, energia idêntica à serial). Lançar com `mpirun -np $SLURM_NTASKS --map-by core --bind-to core` (+ `-x OMP_NUM_THREADS -x OMP_PLACES -x OMP_PROC_BIND` no híbrido); conferir `--report-bindings`.
- `Pcrystal` lê o arquivo `INPUT` do diretório; o `crystalOMP` lê o stdin (o job faz os dois).
- `properties` (pasta `_omp`) também é OpenMP (4 threads: TCPU/TELAPSE ≈ 3,9).
- O job imprime o `cpuset=` no início: conferir. Em dúvida, `OMP_DISPLAY_AFFINITY=TRUE`.

## 3. Armadilhas (lista completa e números em `references/gotchas.md`)

Rótulos de BAND por nome limitados às Tabelas 14.1/14.2 (FCC não tem K) → usar `cry_kpath.py` · BAND depois de NEWK destrói os autovetores (ordem BAND→NEWK→DOSS) · NEWK com IFE=1 (obrigatório com SPINLOCK/LEVSHIFT) · `DOSS.DAT` já em E−E_F (Ha), projeções na ordem do PROPS e total por último · gap: "banda ocupada se max ≤ E_F" erra quando o VBM está fora da rede SCF · SMEAR → gradiente numérico · `fort.34` só existe se a otimização convergiu (senão `opt_steps/optcNNN`) · RESTART exige o mesmo INPUT + `OPTINFO.DAT` + `fort.9` · `TRUST RADIUS TOO SMALL` → recomeçar da última `optcNNN` · perturbar posição especial à mão quebra a simetria (átomos sobrepostos: `NEIGHB ... SMALLDIST`).

## Mapa de referências

| Arquivo | Quando abrir |
|---|---|
| `references/CRYSTAL23_Manual.md` | qualquer keyword, erro ou método novo (só via `grep -n`; índice no topo) |
| `references/workflow.md` | cada etapa com INPUT comentado, critérios, restart, spin, convergência de SCF, leitura de saída |
| `references/gotchas.md` | fatos verificados (harpia, tempos, Ag2SeO3, testes MgO/TiO2), erros vistos |
| `references/build_crystal_manual.py` | regenera o manual indexado a partir do texto do PDF |

## Ao fechar uma etapa
Atualizar a nota do projeto em `~/cofre/02_Memory/<código>/<material>.md` e o `active_session.md`; commit+push do cofre. Fatos novos e verificados do CRYSTAL entram em `references/gotchas.md` deste repo (com data).
