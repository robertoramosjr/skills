---
name: vasp-pipeline
description: Metodologia, templates e armadilhas para cálculos VASP (PAW-PBE) do usuário no cluster SLURM (access/coaraci) — convergência ENCUT/k-points (2×ENMAX p/ stress, 1.125×ENMAX p/ Etot), relaxação ISIF=3/ISIF=2, DOS/bandas/magnetismo, slabs e energia de superfície (Wulff), dopagem/defeitos e energia de formação, datasets "rattle" para ML (DeepMD), DFPT/Born/phonopy, Wannier90. Use SEMPRE que o usuário for iniciar, retomar ou depurar um cálculo VASP (POSCAR, INCAR, KPOINTS, POTCAR, OUTCAR, OSZICAR, vasprun.xml, vasp_std, job.sh), pedir convergência de ENMAX, "stress", "Etot", slabs, vacâncias, BaZrS3/Co3O4/Ag2CrO4/NaCoO2/YSZ/ZrO2/TiNbTa, ou comparar VASP com Turbomole/CP2K — mesmo sem dizer "VASP" explicitamente.
---

# Pipeline VASP

Metodologia usada nos projetos do usuário (BaZrS3, Co3O4, Ag2CrO4, NaCoO2, YSZ/ZrO2, Ti15Nb4Ta1, alizarina/Cu-Ni-Zn em molécula). Tudo aqui foi extraído de cálculos reais; onde algo não foi verificado, está dito.

**Por que existe:** VASP é o código "de casa" do usuário e a referência mental de todos os outros (ISIF, NBANDS, ICHARG=11). Erros silenciosos aqui (pasta copiada com `vasprun.xml` idêntico, lotes incompatíveis, job travado 17 h sem OUTCAR) já invalidaram tabelas inteiras de um paper. Por isso: checar dados antes de usar, nunca assumir.

## 0. Regras duras (do usuário)

1. **Reportar custo (núcleo-h / walltime) antes de submeter** algo além de testes de minutos; nada pesado no login node.
2. **Não decidir arquitetura/escopo sozinho** (quais planos, quais terminações, quais dopagens, nível de teoria) — reportar e perguntar.
3. **Validar por arquivo de saída, não por estado da fila:** `OUTCAR` com `reached required accuracy` (relax) ou convergência eletrônica limpa (estático); `OSZICAR` sem `DAV: 100` repetido (sloshing). `scancel`/TIMEOUT deixam `CONTCAR` parcial.
4. **Nunca confiar em número de apresentação/póster antigo** sem rastrear ao `vasprun.xml`/CSV de origem; já houve RMSE, EoS e curvas "fabricados" e `vasprun.xml` MD5-idêntico entre pastas diferentes (`md5sum` antes de agrupar réplicas).
5. Scripts: inglês, `argparse`, docstring com `Usage:`, sem hardcode; ficam em `~/work_vasp/scripts/` (repo `computational-materials-scripts`). Jobs só em FS compartilhado, nunca `/tmp`.

## 1. Convenção de convergência (a "marca" do grupo)

| Etapa | ENCUT | ISIF | Pasta típica | Para quê |
|---|---|---|---|---|
| Stress/volume | **2 × ENMAX** (maior ENMAX dos POTCAR) | 3 (célula + íons) | `paw_pbe_2xENMAX_Stress[_OK]` | estrutura de equilíbrio sem stress de Pulay |
| Energia total | **1.125 × ENMAX** | 2 (só íons, célula do passo anterior) | `paw_pbe_1.125ENMAX_Etot` | energias comparáveis (defeitos, fases) |
| DOS / bandas | 1.125 × ENMAX | estático (NSW=0) | `…_DOS`, `…_bands` | propriedades eletrônicas |

Motivo do 2×ENMAX: a base de ondas planas fica fixa na célula inicial; com a célula variando, o stress só converge com cutoff alto. Daí o 2º passo ISIF=2 (reconstrói a base na célula final). Sufixo `_OK` na pasta = validada pelo usuário. Exemplo (BaZrS3): ENCUT 692.728 (stress) e 389.6595 (Etot) ⇒ ENMAX 346.364.

Sempre convergir k-points por densidade, com critério explícito (meV/átomo e %V), antes do ENCUT final dos produtos — ver `references/workflow.md`.

## 2. INCAR base do grupo (resumo; completo em `references/incar-job.md`)

`GGA=PE`, `PREC=Accurate`, `ALGO=Normal`, `EDIFF=1E-6`, `EDIFFG=-0.01`, `NELM=1500`, `NELMIN=6`, `NELMDL=-8`, `AMIX=0.4`, `BMIX=0.0001`, `ISMEAR=0`/`SIGMA=0.01`, `LASPH=.TRUE.`, `ADDGRID=.TRUE.`, `LREAL=Auto`, `IBRION=2`, `POTIM=0.5`, `NSW=800`, `LORBIT=10`, `NWRITE=1`, `LWAVE/LCHARG=.FALSE.` (ligar só quando precisar), `NCORE=4`, `LPLANE=.TRUE.`. Spin: `ISPIN=2` + `MAGMOM` explícito (Co3O4/Ag2CrO4/NaCoO2 magnéticos; comparar ordem paralela × antiparalela). Híbrido: `LHFCALC`, `AEXX=0.25`, `HFSCREEN=0.206` (HSE06), `PRECFOCK`. Slab/molécula polar: `IDIPOL=3` + `LDIPOL=.TRUE.`.

## 3. Cluster

- **VASP SEMPRE com `mpirun -np $SLURM_NTASKS vasp_std`, NUNCA `srun`** (o binário é compilado com Intel/Intel MPI; `srun` não serve — regra do usuário, 2026-10-21; em abr/2026 um script chegou a trocar para `srun` "por compatibilidade" e estava errado).
- **access:** `module load miniconda intel/mpi/2017 vasp/6.4.3`, `mpirun -np $SLURM_NTASKS vasp_std > saida.out`, `rm -f STOPCAR` antes, `ulimit -s unlimited`. Header típico `-N 2 --ntasks-per-node=8`, `-t 24:00:00` (stress: 5 d). Variáveis Intel MPI: `I_MPI_HYDRA_BOOTSTRAP=slurm`, `I_MPI_FABRICS=shm:ofi`, `I_MPI_PIN=1`, `OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`, `MKL_NUM_THREADS=1`.
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
