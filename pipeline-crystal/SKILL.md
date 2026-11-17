---
name: pipeline-crystal
description: RITO OBRIGATÓRIO em CRYSTAL23 (sempre nesta ordem - 1 convergência de k-points (SHRINK) com malhas por comprimento l como o "Auto" do VASP, 2 escolha da malha pelo usuário, 3 otimização de célula+íons OPTGEOM/FULLOPTG (= stress, ISIF=3), 4 relaxação iônica OPTGEOM/ATOMONLY na célula final (= Etot, ISIF=2), 5 DOS/PDOS e bandas via properties (NEWK/DOSS/BAND) para GGA (PBE/PBEsol) e híbridos (HSE06/PBE0/B3LYP)). Gaussianas (pob-TZVP-rev2, ECP), harpia (crystalOMP 23.1.0.1), manual oficial CRYSTAL23 indexado em references/ para consulta via grep. Use SEMPRE que o usuário for iniciar, retomar ou depurar algo em CRYSTAL (INPUT/d12, d3, crystal.out, fort.9, fort.34, fort.25, DOSS.DAT, BAND.DAT, OPTINFO.DAT, SHRINK, TOLINTEG, FULLOPTG, ATOMONLY, NEWK, DOSS, BAND, crystalOMP, properties, work_crystal), pedir bandas/DOS com funcional híbrido em sólido, ou "faz no CRYSTAL o que fazíamos no VASP/CP2K" — mesmo sem dizer "CRYSTAL".
---

# Pipeline CRYSTAL23

CRYSTAL (LCAO, Gaussianas) entrou para fazer **bandas/DOS com funcional híbrido e k-points**, o que travou nos outros códigos: no CP2K o RI-HFXk bate no muro de memória (`cp2k-pipeline` §5) e o `riper` do TURBOMOLE não tem gradiente com híbrido (teste 875, 2026-11-17, `$grad missing`). No CRYSTAL o híbrido custa mais no SCF, mas **bandas e DOS saem do `fort.9` sem custo extra de troca exata** (são diagonalizações da matriz de Fock já convergida). VASP continua sendo a referência mental: o rito abaixo é o do `vasp-pipeline` traduzido.

> ➡️ **MANUAL OFICIAL — consulte SEMPRE antes de adivinhar:** `references/CRYSTAL23_Manual.md` (CRYSTAL23 User's Manual, 31/10/2023; 28,9 mil linhas, 2 MB; vem no `git pull`). **Nunca ler inteiro:** `grep -n -i` e depois `sed -n 'A,Bp'`. O topo do arquivo tem índice com linha: **A** = sumário (seção → página → linha), **B** = keywords do pipeline (SHRINK, TOLINTEG, FULLOPTG/ATOMONLY, FINALRUN, EXTPRESS, BAND, NEWK, DOSS, HSE06, grades...), **C** = página → linha (resolve as referências "see page N" do texto). O texto veio de PDF: tabelas viram `|` quebrados e palavras grudam (`thekeywordFOO`), então buscar com `-i` e com pedaço da palavra. Ex.: `grep -n "^- SHRINK\|^- NEWK" references/CRYSTAL23_Manual.md` → `sed -n '6708,6800p' ...`. Regenerar: `references/build_crystal_manual.py`.

## 🚨 O RITO — OBRIGATÓRIO, SEMPRE NESTA ORDEM

> Toda estrutura nova começa pela convergência de k-points. Nunca pela DOS, nunca com SHRINK "razoável" escolhido à mão (a mesma falha registrada no VASP em 2026-11-09).

| # | Etapa | Equivalente VASP | CRYSTAL | Fecha a etapa |
|---|---|---|---|---|
| **1** | **Convergência de k** | `KPOINTS Auto`, l = 05…50 | `cry_input.py --mode kconv --klengths "5 10 … 40"` → SP por malha (`--kconv-opt` = FULLOPTG por malha, paridade total com o rito VASP, caro) | `cry_parse.py kconv … --csv`: ΔE meV/átomo e gap vs a malha mais densa (ΔV % se `--kconv-opt`) |
| **2** | **Escolha da malha** (propor, **o usuário decide**) | idem | malha do **platô**: nem a menor nem a maior | malha registrada no plano |
| **3** | **Stress: célula + íons** | ISIF=3 (2×ENMAX) | `--mode fullopt` (`OPTGEOM` + `FULLOPTG`; FINALRUN 4 é default) | `OPT END - CONVERGED` + `fort.34` |
| **4** | **Etot: só íons, célula fixa** | ISIF=2 (1.125×ENMAX) | `--mode atomopt --geom <etapa3>/fort.34` (`EXTERNAL` + `ATOMONLY`) | `OPT END - CONVERGED`; energia comparável |
| **5** | **DOS + bandas** | estático, malha 3×, `NEDOS=6001` | SP na geometria da etapa 4 (`--mode sp`) → `cry_props.py` → `properties`: **BAND → NEWK → DOSS** (nessa ordem) | `bands.csv`, `DOS_raw_data.csv`, gap/tipo |

**Por que manter 3 e 4 separadas se não há ENCUT?** A base gaussiana acompanha os átomos (não há stress de Pulay de base de ondas planas fixa), mas a **classificação das integrais (FIXINDEX) fica presa à geometria inicial** durante a otimização (manual §7.4.1, índice B "Integrals classification"): o ATOMONLY partindo do `fort.34` reclassifica tudo na célula final. Também mantém o protocolo idêntico ao do VASP (energias de defeitos/fases sempre a célula fixa). **Não trocar base, ECP, TOLINTEG nem grade entre etapas** (o análogo de "não trocar POTCAR").

**Malha k no CRYSTAL:** `SHRINK IS ISP` (isotrópica) ou `SHRINK 0 ISP` + `IS1 IS2 IS3` (anisotrópica; o gerador põe `NOSYMADA`, exigido pelo manual p.125 — testado com 16 operações no TiO2). ISP (rede de Gilat) = 2×IS1, irrelevante em isolante mas obrigatório. As malhas `--klengths` usam a regra do `Auto` do VASP: `N_i = max(1, int(l·|b_i| + 0.5))`, |b_i| da **célula primitiva** sem 2π (grupo centrado → `--cell-from crystal.out|fort.34`). Supercélula: dividir as subdivisões pelo fator do eixo, arredondando para cima (regra do VASP).

**DOS/bandas (regras do usuário herdadas do VASP, 2026-11-11):** rede da DOS (NEWK) = **3× a malha do SCF em cada eixo**, ISP = 2×IS; **NPT = 6001** (o "NEDOS") e NPOL 18; PDOS por elemento (gerado do `crystal.out`). Caminho de bandas: rótulos só valem se estiverem nas Tabelas 14.1/14.2 do manual (FCC aceita só X, L, W; **K não existe** → usar `--path-frac`). Gap e tipo: comparar o do caminho (`cry_parse.py bands`) com o da rede SCF (última linha `ENERGY BAND GAP` do `crystal.out`).

**GGA × híbrido:** o mesmo rito vale para os dois; só muda `--func` (GGA: `PBE`, `PBESOL`; híbridos: `HSE06`, `HSESOL`, `PBE0`, `PBESOL0`, `B3LYP`...). **Decisão do usuário, não minha:** geometria própria para cada funcional (rito completo com cada um) ou híbrido em SP sobre a geometria GGA (rotular `HSE06//PBE`). Range-separated (HSE06) desliga a expansão bipolar da troca: custa 2–3× um híbrido global (manual p.138).

## 0. Regras duras

1. Chat em português; scripts/comentários/argparse em inglês.
2. **Reportar custo (núcleo-h, walltime) antes de qualquer `sbatch`**; um passo por vez; nada pesado no login (teste de segundos com 2–4 threads é aceito, como MgO/TiO2 abaixo).
3. **Validar por texto, nunca por exit code/`sacct`:** `EEEEEEEEEE TERMINATION` + `SCF ENDED - CONVERGENCE` (+ `OPT END - CONVERGED` em OPTGEOM). `cry_parse.py check` faz isso. Properties: `TERMINATION` e nenhum `ERROR ****`.
4. **Limites padrão:** SCF `MAXCYCLE 1500`, OPTGEOM `MAXCYCLE 800` (mesma regra do CP2K/VASP). OPTGEOM `TOLDEE` ≥ TOLDEE do SCF (manual p.193).
5. **Usar o grupo espacial real** (arquivo `crygeo` com unidade assimétrica), não P1: o custo cai com o nº de operações (TiO2: P1 = 19 k-pontos na IBZ, P4₂/mnm = 9). POSCAR vira P1 com aviso. Os runs atuais do Ag2SeO3 (`~/work_crystal`, 2026-11-17) estão em **P1** (24 at.); a célula é monoclínica (β = 91,13°) — conferir o grupo (P2₁/c = 4 operações) antes de reescrever como `crygeo`.
6. **harpia: 900 MB/CPU** → `--mem=43200M` com 48 CPUs; crystalOMP = 1 processo × 48 threads OpenMP.
7. **Watchdog obrigatório** (`~/skills/global/job_watchdog.sh`), mas o `run_watched` põe o comando em background e o bash troca o stdin por `/dev/null`: **`run_watched crystalOMP < INPUT` morre com `END OF DATA IN INPUT DECK`**. Usar `run_watched bash -c '"$0" < INPUT' "$BIN/crystalOMP"` (já no `job_crystal.sh`; verificado 2026-11-17).
8. Não decidir sozinho: funcional, base, malha final, geometria por funcional, spin/ordem magnética.

## 1. Arquivos e scripts (`scripts/`, testados em runs reais em 2026-11-17)

| Script | Faz |
|---|---|
| `cry_input.py` | gera `runs/<nome>/INPUT` p/ `kconv`/`fullopt`/`atomopt`/`sp`; geometria `crygeo` (preferida), `fort.34` (EXTERNAL, copia o arquivo) ou POSCAR (P1); base por arquivo (`--basis-dir basis --basis-tag pob-TZVP-rev2`, checa o Z do ECP, ex. 247 = Ag) ou `--basisset POB-TZVP-REV2`; `--spin/--spinlock/--levshift/--guessp/--restart-opt/--extra3` |
| `cry_props.py` | gera `PROPS` (BAND → NEWK → DOSS) lendo elétrons, nº de AO, átomos e SHRINK do `crystal.out` |
| `cry_parse.py` | `check`, `kconv` (CSV), `opt` (célula/volume finais), `dos` (→ `DOS_raw_data.csv`, eV), `bands` (→ `bands.csv`, VBM/CBM/gap no caminho) |
| `job_crystal.sh` | `sbatch job_crystal.sh <rundir>` (SCF/OPT) ou `sbatch -t 02:00:00 job_crystal.sh <rundir> props`; scratch em `~/scratch/crystal23/<job>`, copia `fort.34`, `fort.9→fort.20`, `OPTINFO.DAT`/`HESSOPT.DAT` de ida e `fort.9 fort.34 OPTINFO.DAT HESSOPT.DAT opt*` de volta; renomeia o `crystal.out` antigo |

Fluxo típico (detalhe, critérios e restart em `references/workflow.md`):
```bash
S=~/skills/pipeline-crystal/scripts
python3 $S/cry_input.py --geom mat.crygeo --basis-dir basis --basis-tag pob-TZVP-rev2 --func HSE06 \
        --mode kconv --klengths "10 15 20 25 30 35" --name hse_kconv           # 1
python3 $S/cry_parse.py kconv runs/hse_kconv_l* --csv kconv.csv                  # 2 (usuário escolhe)
python3 $S/cry_input.py ... --mode fullopt --k 4 2 3 --name hse_fullopt          # 3
python3 $S/cry_input.py --geom runs/hse_fullopt/fort.34 ... --mode atomopt --k 4 2 3 --name hse_atomopt  # 4
python3 $S/cry_input.py --geom runs/hse_atomopt/fort.34 ... --mode sp --k 4 2 3 --name hse_sp            # 5a
python3 $S/cry_props.py --scf-out runs/hse_sp/crystal.out --what both --path-frac "..."                 # 5b
sbatch $S/job_crystal.sh runs/hse_sp props; python3 $S/cry_parse.py bands runs/hse_sp; python3 $S/cry_parse.py dos runs/hse_sp
```

## 2. Cluster (harpia, único verificado)

`module load modmat/crystal/23.1.0.1` + **`LD_LIBRARY_PATH=/opt/intel/oneapi/compiler/2026.2/lib:$LD_LIBRARY_PATH`** (runtime Intel do binário). Binários em `$CRY23_ROOT/bin/Linux-ifort_i64_omp/v1.0.1/` (`crystalOMP`, `PcrystalOMP`, `properties`, `Pproperties`) e `Linux-ifort_i64/` (puros MPI/seriais). Partição `par48a`, 3 d. `PcrystalOMP` (MPI+OpenMP) ainda **não testado**; para células grandes, testar antes de assumir ganho. access/coaraci: CRYSTAL não verificado.

## 3. Armadilhas (lista completa e números medidos em `references/gotchas.md`)

Stdin perdido no `run_watched` (regra 7) · rótulos de BAND limitados às Tabelas 14.1/14.2 (`ERROR **** BANDE **** UNKNOWN K-POINT SYMBOL`) · BAND **depois** de NEWK destrói os autovetores do NEWK (ordem fixa BAND→NEWK→DOSS) · NEWK com IFE=1 sempre (obrigatório com SPINLOCK/LEVSHIFT) · `DOSS.DAT` já vem em **E − E_F (hartree)**, colunas = projeções na ordem do PROPS e o **total por último** · janela de bandas da DOS incluindo caroço espalha os 6001 pontos (passo > 20 meV → estreitar INZB/IFNB) · SMEAR (condutor) → gradiente analítico incompleto, usar numérico (manual p.196) · `crystal.out` não é anexado: o job guarda o anterior com carimbo de data · RESTART de OPTGEOM exige o **mesmo INPUT** + `RESTART` + `OPTINFO.DAT` + `fort.9` (vira `fort.20`) e `MAXCYCLE` conta a partir do último passo · `TRUST RADIUS TOO SMALL` → recomeçar da última `optcNNN` (EXTERNAL).

## Mapa de referências

| Arquivo | Quando abrir |
|---|---|
| `references/CRYSTAL23_Manual.md` | qualquer keyword, erro ou método novo (só via `grep -n`; índice no topo) |
| `references/workflow.md` | cada etapa do rito com INPUT comentado, critérios, restart, spin, convergência de SCF, leitura de saída |
| `references/gotchas.md` | fatos verificados (harpia, tempos, Ag2SeO3, testes MgO/TiO2), erros vistos |
| `references/build_crystal_manual.py` | regenera o manual indexado a partir do texto do PDF |

## Ao fechar uma etapa
Atualizar a nota do projeto em `~/cofre/02_Memory/<código>/<material>.md` e o `active_session.md`; commit+push do cofre. Fatos novos e verificados do CRYSTAL entram em `references/gotchas.md` deste repo de skills (com data).
