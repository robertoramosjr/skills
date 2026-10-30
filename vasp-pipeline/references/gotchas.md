# Armadilhas VASP e de dados

- **Núcleos ociosos no job (2026-10-30, access):** os 300 estáticos do rattle (job 4958027) pediam `--ntasks-per-node=4 --cpus-per-task=8` (32 cpus cobradas) mas `mpirun -np $SLURM_NTASKS` lançava só **4 ranks** (OUTCAR: `running 4 mpi-ranks`); o `vasp_std` não usa OpenMP, então 28 de 32 cpus ficaram paradas (4,1 h/frame, 131 núcleo-h cobrados, ~16 úteis). **Regra:** `ntasks × cpus-per-task` = cpus que o VASP realmente usa; conferir `running N mpi-ranks` no OUTCAR e `NumCPUs` no `scontrol`. Nós da access: `S:C:T 2:14:2`, 56 cpus = 28 núcleos físicos, **52 cpus úteis (`CPUEfctv`) = 26 núcleos**; `-n 56` é recusado (`Requested node configuration is not available`). Receita sem ocioso: 1 rank por núcleo físico, `--ntasks-per-node=24 --cpus-per-task=2`, `OMP_NUM_THREADS=1`, `I_MPI_PIN_DOMAIN=core`; INCAR `KPAR × NCORE = ntasks` com KPAR dividindo NKPTS (16 k-pontos: KPAR=8, NCORE=3). Antes de arrays grandes: 1 frame-teste e comparar tempo.

- **Nunca lançar o VASP com `srun`** (2026-10-21): o binário é compilado com Intel/Intel MPI e só roda com `mpirun -np $SLURM_NTASKS vasp_std`. Uma versão antiga de `bash_stress.sh` (remoto, abr/2026) trocava `mpirun` por `srun` com o comentário "compat. Intel MPI" — errado; ao mesclar scripts, a versão com `mpirun` é a certa.

- **Cópia acidental de resultados:** `CaSv_struc2` e `CaBa_struc2` tinham `vasprun.xml` MD5-idêntico a `Bav_struc2`. Rodar `md5sum */vasprun.xml | sort | uniq -w32 -d` antes de montar tabelas.
- **Dois lotes incompatíveis** (`_struc` × `_OK`) divergindo 0,7–0,8 eV para estruturas com Ca (≈0,003–0,07 eV para vacâncias puras): comparar apenas dentro de um lote; documentar quando misturar.
- **Slab com normal inclinada + `IDIPOL=3`** não convergia o SCF (mono ZrO2): célula com c ⟂ superfície e ∥ z.
- **CONTCAR de FCC relaxou para bcc** (caminho de Bain) — a energia não era E_fcc; checar a rede após relaxar antes de usar como referência de fase.
- **Cálculo parcial lido como final:** `scancel`/TIMEOUT deixam CONTCAR/OUTCAR parciais; exigir `reached required accuracy`.
- **Nome de pasta mente** (`…_d3` com `IVDW=0`): conferir INCAR.
- **Pastas pesadas** (`HUBBARD_CORRECTION` ~93 G, `vasprun.tar.gz`): nunca versionar nem linkar; referenciar por caminho.
- **Apresentação/póster:** gerar números só a partir de arquivos reais; valores sem output no disco não entram (RMSE, EoS, MD).
- **Fila:** `(Priority)` não é erro. Arrays de milhares de pastas: usar `check_queue.py`, não `squeue` isolado.
- **VASP 6.6.1 na coaraci:** nó inteiro (48); `par48-x` 3 d; PBE ~125–150 s/ciclo, HSE06 ~1000 s/ciclo para ~100 átomos (CP2K/Turbomole, ordem de grandeza); `aoforce`/phonons grandes estouram 3 d.
- **pymatgen:** `Slab.is_polar()` sem oxidação = False sempre; `SlabGenerator` gira a rede por padrão; `get_tasker2_slabs()` falha em alguns Tasker III.
- **Dataset DeepMD / symlink-farm (2026-10-19):** `build_dataset_v2.py chunks` criou `vasprun.xml -> ./<sistema>/...` (relativo ao próprio link) → 3861 links quebrados; `extract` imprimiu `Total frames read: 0` mas o job saiu com exit 0 e o `merge` seguiu só com dado antigo (`frames_in_pool_fresh: 0`, sem `test_rattle`). Sempre conferir `find -L chunks -name vasprun.xml | wc -l` e `frames_in_pool_fresh` no `report.json` antes de treinar; links devem ser absolutos. Loop bash com `readlink` por arquivo estoura 120 s no NFS: usar Python (`os.walk`).
- **Treino DeepMD (medido 2026-10-19):** se_e2_a, rcut 6, fitting 240³, ~1100 frames de 80 átomos: 0,0185 s/batch na GPU do grid → 400k passos ≈ 2,1 h/seed; ensemble de 4 ≈ 8,5 GPU-h.
- **E_f só de run convergido (2026-10-20):** timeout deixa `vasprun.xml` sem `</modeling>` e com 1–6 passos; `e_fr_energy[-1]` parece válido mas é energia de passo inicial (BaZrS3 Ca_Ba: 1,531 vs 0,701 eV convergido). Antes de qualquer tabela: exigir `</modeling>`, fmax final <|EDIFFG| (varray `forces`) e nº de passos >1; pasta duplicada com energia idêntica = cópia.

## Watchdog de walltime: STOPCAR `LABORT`, não `LSTOP` (2026-10-21, NaCoO2 Nd_Ov/Nd_NaV)
- `LSTOP=.TRUE.` só age no fim do passo **iônico**; com 255 átomos/NBANDS 1560 o SCF dura horas e o watchdog dava `kill -9` após a graça → `WAVECAR`/`CHGCAR` com 0 byte → todo reenvio recomeçava do zero (13 reenvios, 0 passos iônicos, E=+7e4 eV).
- Com `ISTART=1`/`ICHARG=1` e CHGCAR vazio o VASP só avisa `CHGCAR is incomplete` e parte de densidade lixo. Use `LABORT=.TRUE.` (para no próximo passo eletrônico e grava WAVECAR) e deixe o `job.sh` escolher `ISTART/ICHARG` por `[ -s WAVECAR ] && [ -s CHGCAR ]`.
- Sintoma de diagnóstico: `OSZICAR` com E de milhares de eV positivos no DAV:1 e `ls -l` de WAVECAR/CHGCAR = 0.
- **DeePMD (2026-10-24):** `dp train` que acaba em `NaN detected` (ex.: `se_atten_v2` @149500, lr ~1e-6) não falha o script do job: o Slurm marca COMPLETED mas não há `graph.pb`/`tests/`. Validar sucesso por `tests/*.log`, nunca por `sacct`. Benchmark de descritor (BaZrS3, 150k): embedding satura (~5 %/dobro), fitting net irrelevante, só `rcut` melhora F.
