---
name: vasp-pipeline
description: RITO OBRIGATÓRIO (sempre nesta ordem - 1 STRESS com convergência de k-points em ISIF=3 a 2×ENMAX, 2 escolha da malha, 3 ETOT ISIF=2 a 1.125×ENMAX, 4 DOS/propriedades; nunca pular o stress nem escolher malha k por palpite). Metodologia, templates e armadilhas para cálculos VASP (PAW-PBE) do usuário no cluster SLURM (access/coaraci) — convergência ENCUT/k-points (2×ENMAX p/ stress, 1.125×ENMAX p/ Etot), relaxação ISIF=3/ISIF=2, DOS/bandas/magnetismo, slabs e energia de superfície (Wulff), dopagem/defeitos e energia de formação, datasets "rattle" para ML (DeepMD), DFPT/Born/phonopy, Wannier90. Use SEMPRE que o usuário for iniciar, retomar ou depurar um cálculo VASP (POSCAR, INCAR, KPOINTS, POTCAR, OUTCAR, OSZICAR, vasprun.xml, vasp_std, job.sh), pedir convergência de ENMAX, "stress", "Etot", slabs, vacâncias, BaZrS3/Co3O4/Ag2CrO4/NaCoO2/YSZ/ZrO2/TiNbTa, ou comparar VASP com Turbomole/CP2K — mesmo sem dizer "VASP" explicitamente.
---

# Pipeline VASP

Metodologia usada nos projetos do usuário (BaZrS3, Co3O4, Ag2CrO4, NaCoO2, YSZ/ZrO2, Ti15Nb4Ta1, alizarina/Cu-Ni-Zn em molécula). Tudo aqui foi extraído de cálculos reais; onde algo não foi verificado, está dito.

**Por que existe:** VASP é o código "de casa" do usuário e a referência mental de todos os outros (ISIF, NBANDS, ICHARG=11). Erros silenciosos aqui (pasta copiada com `vasprun.xml` idêntico, lotes incompatíveis, job travado 17 h sem OUTCAR) já invalidaram tabelas inteiras de um paper. Por isso: checar dados antes de usar, nunca assumir.

## 🚨 O RITO — OBRIGATÓRIO, SEMPRE NESTA ORDEM (leia antes de criar QUALQUER pasta de cálculo)

> **TODA estrutura nova (material, supercélula-mãe, fase de referência, constituinte elementar, óxido para μ) COMEÇA PELO STRESS. Nunca pela energia total, nunca pelo DOS, nunca com malha k "razoável" escolhida à mão.**
> Falha registrada em 2026-11-09 (Ag2CrO4:Nd): Nd2O3/Ag2O/Cr2O3 foram montados com malhas k por palpite e ISIF=2 direto (jobs 1910439/1911421, cancelados antes de rodar). O usuário corrigiu: *"primeiro stress, depois etot, depois dos"*.

| # | Etapa | ENCUT | ISIF | Malha k | Pasta | Saída que fecha a etapa |
|---|---|---|---|---|---|---|
| **1** | **STRESS + convergência de k-points** | **2 × ENMAX** (maior ENMAX dos POTCAR) | **3** (célula + íons) | `KPOINTS` modo **Auto**, comprimento `l = 05…50` (passo 5), uma pasta por `l` | `paw_pbe_2xENMAX_Stress[_OK]` | `dados_convergencia_final.csv` (Kdensity, Kmesh, Lattice_Param, Energy, Pasta) |
| **2** | **Escolha da malha** (decisão do usuário: propor, não decidir) | — | — | a malha onde a energia **já saturou**, **nem a maior** (custo) **nem a menor** (garantir que estamos num ponto otimizado) | — | malha explícita Γ-centrada (`GAMMA` + `N1 N2 N3`) registrada no plano |
| **3** | **ETOT** | **1.125 × ENMAX** (mesmo ENMAX) | **2** (só íons; célula do stress) | a malha escolhida no passo 2 | `paw_pbe_1.125xENMAX_Etot` | `OUTCAR` com `reached required accuracy`; energias comparáveis |
| **4** | **DOS / bandas / propriedades** | 1.125 × ENMAX | estático (`NSW=0`), `ISTART=1`/`ICHARG=1` do Etot | a do Etot (ou mais densa, `KPOINTS_OPT`) | `paw_pbe_1.125xENMAX_DOS`, `_bands` | `DOS_raw_data.csv` etc. |

**Como o stress foi feito no Ag2CrO4 (modelo a copiar):** `INCAR` com `ENCUT=829.270` (=2×414.635, o **ENMAX do O_GW**, maior entre Ag_GW 249.844, Cr 227.080, O_GW 414.635), `ISIF=3`, `NSW=800`, `IBRION=2`; `KPOINTS` com `Auto` e o comprimento escrito como `XX`; o script cria `05/ 10/ … 50/`, copia `INCAR POSCAR KPOINTS POTCAR`, troca `XX`→`l` com `sed`, e dentro de cada pasta **repete o ISIF=3 (`CONTCAR`→`POSCAR`, `OSZICAR_n`, `OUTCAR_n`) até o `OSZICAR` ter uma única linha `F=`** (máx. 50 repetições): é isso que reconstrói a base de ondas planas na célula final. Scripts: `bash_stress_coaraci.sh` (coaraci, com resubmissão por tempo) e `bash_stress.sh` (access), em `~/work_vasp/scripts/`; tabela por `extract_stress_data.py`. Exemplo real (28 átomos, Ag2CrO4): `l=15` está −0,37 meV/átomo de `l=35`; de `l=20` a `l=50` tudo fica dentro de 0,01 meV/átomo (saturado) → escolhido **`l=35` (6×5×3)**, que entrou no `KPOINTS` do Etot e do DOS.

**Cronologia no Ag2CrO4 (referência):** stress da célula de 28 átomos (`paw_pbe_2xENMAX_Stress_OK`, `l=05…50`) → escolha 6×5×3 → Etot do mesmo material (`paw_pbe_1.125xENMAX_Etot`, `ISIF=2`, `ENCUT=466.464375`) → constituintes e fases de referência pelo mesmo rito (`pristine_materials_stress/` → `pure_athoms/`) → supercélulas pristina e dopadas (112 e 222–224 átomos) sobre a célula do Etot, `ISIF=2` → DOS estático (`paw_pbe_1.125xENMAX_DOS`, `NSW=0`, `ISTART=ICHARG=1`).

**Checklist antes de qualquer `sbatch` numa estrutura nova (se algum "não", pare):**
1. Existe pasta de stress convergida em k para esta estrutura (tabela `dados_convergencia_final.csv`)? Se não, **o primeiro job é o stress**.
2. A malha do Etot veio da tabela e foi aprovada pelo usuário (passo 2), não de palpite?
3. ENCUT = 2×ENMAX no stress e 1.125×ENMAX no Etot, com o **mesmo** ENMAX (maior dos POTCAR da própria estrutura)?
4. Constituintes/referências (μ) seguiram o mesmo rito e o **mesmo spin** (`ISPIN`) das células que vão comparar?
5. Custo reportado antes do `sbatch`; um passo por vez; nada de polling.

**Regras acrescentadas pelo usuário (2026-11-09):**
- **Fases de referência (μ, óxidos, constituintes) usam os MESMOS POTCAR do material hospedeiro**, com o mesmo ENCUT derivado do maior ENMAX do hospedeiro. Ex.: para CrO3/Cr2O3 usar o `Cr` (06Sep2000) e o `O_GW` (28Sep2005) do Ag2CrO4; Nd2O3 → `Nd` (25May2002) + `O_GW`; Ag2O → `Ag_GW` + `O_GW`. Conferir por comparação byte a byte dos blocos do POTCAR com o do hospedeiro (feito em 2026-11-09 para Nd2O3/Ag2O/Cr2O3/O2: idênticos).
- **Não há troca de POTCAR entre stress e Etot** (nem entre Etot e DOS): copiar o mesmo arquivo em todas as etapas.
- **Malha k das supercélulas:** dividir as subdivisões da malha escolhida na célula original pelo fator de cada eixo da supercélula, **arredondando para cima** os não inteiros; se der 1×1×1 usar **Γ-only**. Ex.: 6×5×3 e supercélula 2×2×2 → 3×3×2.
- **Critério de escolha de l:** qualquer `l` dentro do platô de saturação serve; no Ag2CrO4 `l=25` ou `l=30` também seriam aceitos. O `l=35` foi escolhido só como garantia de que a energia não oscila. Escolher um `l` do platô com folga, sem ir ao maior.
- **Sufixo `_OK` na pasta** = sinal do usuário de que **o cálculo daquela pasta terminou**. Não é garantia de convergência: validar por OUTCAR/OSZICAR.

**Moléculas em caixa (O2 etc.) — NUNCA feito antes pelo usuário; protocolo PROPOSTO, a validar com ele (pesquisa de 2026-11-09, ver fontes abaixo):**
- Não há stress/ISIF=3 (a célula é só uma caixa): a "etapa 1" vira **convergência do tamanho da caixa** (série de lados, ex. 10, 12, 14, 16 Å, caixa **ortorrômbica** com lados diferentes) a ENCUT = 1.125×ENMAX do hospedeiro, mesmo POTCAR; critério em meV/molécula; usuário escolhe.
- **Γ-only** (`KPOINTS` `GAMMA 1 1 1`): um ponto k basta para átomo/molécula isolados; `ISPIN=2`; O2 é **tripleto**: `NUPDOWN=2` (ou `MAGMOM = 2 2`); `ISMEAR=0` com `SIGMA` pequeno (0.01–0.05), pois os níveis são discretos; `ISYM=0` ajuda estados degenerados; energia a reportar = *energy without entropy*.
- Depois: Etot com `ISIF=2` (relaxa a ligação) na caixa escolhida.
- **Ressalva conhecida:** PBE superestima a ligação do O2 (energia de ligação ~6,7 eV vs 5,2 eV experimental, em PW91); se o μ_O vier de O2, decidir com o usuário se aplica correção. Fontes: [VASP tutorial Molecules](https://vasp.at/tutorials/latest/molecules/part1), [fórum: O2/O, NUPDOWN](https://vasp.at/forum/viewtopic.php?p=1458), [fórum: caixa e ISYM](https://vasp.at/forum/viewtopic.php?p=9089), [fórum: SIGMA em O2](https://vasp.at/forum/viewtopic.php?p=1353). A convergência de caixa **não** consta nesses links; é proposta nossa.
- Slabs: ainda por documentar.

## 0. Regras duras (do usuário)

1. **Reportar custo (núcleo-h / walltime) antes de submeter** algo além de testes de minutos; nada pesado no login node.
2. **Não decidir arquitetura/escopo sozinho** (quais planos, quais terminações, quais dopagens, nível de teoria) — reportar e perguntar.
3. **Validar por arquivo de saída, não por estado da fila:** `OUTCAR` com `reached required accuracy` (relax) ou convergência eletrônica limpa (estático); `OSZICAR` sem `DAV: 100` repetido (sloshing). `scancel`/TIMEOUT deixam `CONTCAR` parcial.
4. **Nunca confiar em número de apresentação/póster antigo** sem rastrear ao `vasprun.xml`/CSV de origem; já houve RMSE, EoS e curvas "fabricados" e `vasprun.xml` MD5-idêntico entre pastas diferentes (`md5sum` antes de agrupar réplicas).
5. Scripts: inglês, `argparse`, docstring com `Usage:`, sem hardcode; ficam em `~/work_vasp/scripts/` (repo `computational-materials-scripts`). Jobs só em FS compartilhado, nunca `/tmp`.

## 1. Convenção de convergência (detalhe da tabela do RITO acima)

| Etapa | ENCUT | ISIF | Pasta típica | Para quê |
|---|---|---|---|---|
| Stress/volume | **2 × ENMAX** (maior ENMAX dos POTCAR) | 3 (célula + íons) | `paw_pbe_2xENMAX_Stress[_OK]` | estrutura de equilíbrio sem stress de Pulay |
| Energia total | **1.125 × ENMAX** | 2 (só íons, célula do passo anterior) | `paw_pbe_1.125ENMAX_Etot` | energias comparáveis (defeitos, fases) |
| DOS / bandas | 1.125 × ENMAX | estático (NSW=0) | `…_DOS`, `…_bands` | propriedades eletrônicas |

Motivo do 2×ENMAX: a base de ondas planas fica fixa na célula inicial; com a célula variando, o stress só converge com cutoff alto. Daí o 2º passo ISIF=2 (reconstrói a base na célula final). Sufixo `_OK` na pasta = o usuário sinaliza que o cálculo daquela pasta terminou. Exemplo (BaZrS3): ENCUT 692.728 (stress) e 389.6595 (Etot) ⇒ ENMAX 346.364.

Sempre convergir k-points por densidade, com critério explícito (meV/átomo e %V), antes do ENCUT final dos produtos — ver `references/workflow.md`.

## 2. INCAR base do grupo (resumo; completo em `references/incar-job.md`)

`GGA=PE`, `PREC=Accurate`, `ALGO=Normal`, `EDIFF=1E-6`, `EDIFFG=-0.01`, `NELM=1500`, `NELMIN=6`, `NELMDL=-8`, `AMIX=0.4`, `BMIX=0.0001`, `ISMEAR=0`/`SIGMA=0.01`, `LASPH=.TRUE.`, `ADDGRID=.TRUE.`, `LREAL=Auto`, `IBRION=2`, `POTIM=0.5`, `NSW=800`, `LORBIT=10`, `NWRITE=1`, `LWAVE/LCHARG=.FALSE.` (ligar só quando precisar), `NCORE=4`, `LPLANE=.TRUE.`. Spin: `ISPIN=2` + `MAGMOM` explícito (Co3O4/Ag2CrO4/NaCoO2 magnéticos; comparar ordem paralela × antiparalela). Híbrido: `LHFCALC`, `AEXX=0.25`, `HFSCREEN=0.206` (HSE06), `PRECFOCK`. Slab/molécula polar: `IDIPOL=3` + `LDIPOL=.TRUE.`.

## 3. Cluster

- **VASP SEMPRE com `mpirun -np $SLURM_NTASKS vasp_std`, NUNCA `srun`** (o binário é compilado com Intel/Intel MPI; `srun` não serve — regra do usuário, 2026-10-21; em abr/2026 um script chegou a trocar para `srun` "por compatibilidade" e estava errado).
- **access:** `module load miniconda intel/mpi/2017 vasp/6.4.3`, `mpirun -np $SLURM_NTASKS vasp_std > saida.out`, `rm -f STOPCAR` antes, `ulimit -s unlimited`. Header típico `-N 2 --ntasks-per-node=8`, `-t 24:00:00` (stress: 5 d). Variáveis Intel MPI: `I_MPI_HYDRA_BOOTSTRAP=slurm`, `I_MPI_FABRICS=shm:ofi`, `I_MPI_PIN=1`, `OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`, `MKL_NUM_THREADS=1`.
- **Sem núcleo ocioso (regra, 2026-10-30):** `ntasks × cpus-per-task` = ranks MPI que o VASP usa (não é OpenMP); INCAR `KPAR × NCORE = ntasks`. access: 52 cpus úteis/nó = 26 núcleos físicos (2 threads/núcleo) → `--ntasks-per-node=24 --cpus-per-task=2`, `I_MPI_PIN_DOMAIN=core`. Detalhe e caso do rattle (4 ranks em 32 cpus): `references/gotchas.md`.
- **Se multi-nó morrer em segundos (`MPI_INIT has failed`) ou travar 15–17 h sem OUTCAR** (malha OFI/UCX instável do access, 2026-09-11): `export OMPI_MCA_pml=ob1 OMPI_MCA_btl=self,sm,tcp OMPI_MCA_btl_ofi_disable=1` antes do `mpirun`. Um `resubmit_watchdog.sh` não pega esse deadlock (o array nunca "fecha").
- **coaraci:** VASP 6.6.1; Slurm aloca **nó inteiro** (48 núcleos) e não há partição de 7 d em CPU (`par48-x` 3 d); array de poucas tarefas desperdiça nó — agrupar runs numa alocação.
- Filas pendentes por `(Priority)` = fairshare, não erro: esperar, não reenviar.

## 4. Mapa de decisão rápido

| Pedido do usuário | Vá para |
|---|---|
| Convergir ENMAX / k-points, relaxar estrutura, estático | `references/workflow.md` §1–2 |
| DOS, bandas, massa efetiva, magnetismo | `references/workflow.md` §3 |
| Slab, γ, Wulff, vácuo/espessura | `references/workflow.md` §4 (e a skill `cp2k-pipeline` se for em CP2K) |
| Dopagem, vacância, energia de formação | `references/workflow.md` §5 |
| Dataset ML (rattle, DeepMD, MD) | `references/datasets-ml.md` |
| INCAR/KPOINTS/job.sh completos, scripts disponíveis | `references/incar-job.md` |
| Estado sujo, lotes divergentes, bugs vistos | `references/gotchas.md` |

## 5. Ao fechar uma etapa
Atualizar a nota do material em `~/cofre/02_Memory/vasp/<material>.md` (path real, status, achados) e o `active_session.md`; commit+push do cofre. Lições novas de método entram em `references/gotchas.md` deste repo de skills.
