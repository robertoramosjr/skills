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

## `COMPLETED` do SLURM não prova VASP ok (2026-10-31, BaZrS3 QbC coaraci)
- Loop de pastas em um job: se faltar POSCAR/KPOINTS, o VASP aborta ("I REFUSE TO CONTINUE") em segundos e o job sai `COMPLETED` rc 0 (~10 min/job em vez de horas).
- Antes do `sbatch`: `ls */POSCAR */KPOINTS | wc -l` = nº de pastas. No loop: `rc=$?` logo após o `mpirun` (não dentro de `$(date)`) e marcar OK/FALHA por `grep -q '</modeling>' vasprun.xml`. Ao voltar: contar vasprun >1 KB, não ler só `sacct`.

## O pulo do stress (2026-11-09, Ag2CrO4:Nd) — NUNCA repetir
Ao montar Nd2O3, Ag2O e Cr2O3 (referências de μ) o assistente escolheu malhas k à mão (9×9×6, 9×9×9, 8×8×8) e partiu de ISIF=3 + ISIF=2 sem a convergência de k-points; dois jobs foram submetidos (1910439, 1911421) e cancelados ainda pendentes. Correto: passo 1 do rito (stress com `Auto` `l=05…50`, ISIF=3, 2×ENMAX, repetição até uma linha `F=`), tabela de convergência, usuário escolhe a malha, só então Etot (ISIF=2, 1.125×ENMAX). Também: Nd/O dos `pure_athoms` ficaram com `ISPIN=1` enquanto as células dopadas são `ISPIN=2` (diferença de 0,75 eV/átomo de Nd no μ).
- **TDOS do DOSCAR dividido por 800 (2026-11-07, Ag2CrO4):** 6 dos 7 complexos de 222 átomos (VASP 6.6.0, build de 08/04/2026) têm o bloco total do `DOSCAR` em escala 1/800 constante (integral em E_F = 2,056 em vez de NELECT = 1645; razão DOSCAR/`vasprun.xml` 799,6–800,4 em todas as energias). O `vasprun.xml` e o PDOS por átomo estão certos; o build de 19/08 não tem o problema. **Regra:** antes de usar o TDOS do DOSCAR, conferir a integral em E_F contra o `NELECT` do OUTCAR (o `plot_dos_per_atom.py` da `vasp_plot` faz e reescala com aviso); gap ou figura tirados do total desses DOSCAR sem conferir saem errados.
- **2026-11-08 — OOM ao trocar DAV→SDA com `ALGO=All` em célula grande (coaraci).** Ag2CrO4:Nd 224 at., NBANDS=1002, 3×3×2 (10 k), par480-x 5 nós × 120 GB, KPAR=5/NCORE=48: os 12 passos DAV de `NELMDL=-12` couberam; o 1º passo SDA (`ALGO=All`) estourou (MaxRSS 122 GB/nó, job 1916277). Em células >200 at. com k-mesh, usar `ALGO=Normal` ou mais nós por grupo de k (KPAR menor) — `ALGO=All` guarda vetores extras por banda.

## 2026-11-09 — LOBSTER 6 e VASP em GPU (coaraci)
- **ICOHPLIST/COHPCAR do LOBSTER 6 com ISPIN=2: os dois spins são DUAS COLUNAS da mesma linha** ("ICOHP (at) eF for spin 1 / for spin 2"), não seções. Parser que trata como seções lê só o spin 1 (ICOHP_dn=0, soma pela metade). Corrigido em `work_vasp/scripts/lobster_summary.py`. Teste de encadeamento barato (28 at., partição `teste` 30 min) achou isso antes dos 112 at.
- **Bader (v1.05):** coordenadas do `ACF.dat` podem sair fora da célula; usar só a coluna CHARGE (conferir soma = nº de elétrons).
- **VASP GPU na coaraci:** build OpenACC `/home/sw/vasp/6.5.0-nvhpc/bin/vasp_std` (nvhpc 24.5, sem módulo). Precisa `LD_LIBRARY_PATH=/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/compilers/extras/qd/lib:/home/sw/hdf5-1.12.3-nvcc/install/lib` e `mpirun` do hpcx (`…/24.5/comm_libs/12.4/hpcx/hpcx-2.19/ompi/bin`). 1 rank/GPU, `KPAR=1`, `NCORE=1`, `gpu-x` sem `--exclusive`. Teste 28 at. (Ag2CrO4, ISPIN=2): F idêntico à CPU, 470 s ≈ 1 nó CPU de 48 núcleos. 112 at.: ver nota ag2cro4 (risco de memória da A30, 24 GB).

## LOBSTER na coaraci: etapa COHP/ICOHP escala mal (2026-11-10)
- Job 1931989 (Ag2CrO4 pristine_112, 832 e⁻, 48 threads OMP): na etapa COOP/COHP/ICOHP o `lobster` usou só ~1500–1700% de CPU (≈16/48) por horas. Projeção + DOS (~35 min) usam melhor; o resto do tempo (~4,5 h) é quase serial por par de ligação.
- Regra do cofre (nó inteiro **usado**): não submeter um único `lobster` por nó com 48 threads. Dividir os `cohpGenerator` do `lobsterin` em vários diretórios (symlink de WAVECAR/POSCAR/INCAR/KPOINTS/POTCAR/vasprun), ~12–16 threads cada, rodando em paralelo (`&` + `wait`), ou várias estruturas ao mesmo tempo. Verificar com `ssh <nó> top -b -n2 -u roarj` após ~10 min (esperado ≈ 4800%).
- Pendente validar: unir `ICOHPLIST`/`COHPCAR` das partes e adaptar `scripts/lobster_summary.py`.

## Política de fila VASP (2026-11-11)
- Usuário: rodar os jobs VASP na `gpu-x` sempre que couberem na A30 (24 GB), com o build OpenACC e a receita acima (`KPAR=1 NCORE=1`, 1 rank/GPU, sem `--exclusive`; array permitido, MaxJobsPU=3). Sonda curta antes de migrar célula grande (224 at./`ALGO=All` não validados). Frames/estruturas independentes → array.

## Malha k do DOS (2026-11-11)
- **NEDOS=6001 sempre** (usuário, 2026-11-11). O DOS 711 do CaZrS3 saiu com NEDOS=3001 (`INCAR` da pasta `_DOS`): conferir/refazer.
- Regra do usuário: DOS sempre com kmesh **3× o do Etot** em cada eixo (CaZrS3: Etot 5×4×3 → DOS 15×12×9, job 711). Não reaproveitar a malha do Etot. `WAVECAR`/`CHG` do Etot vêm vazios com `LWAVE/LCHARG=.FALSE.` → DOS parte de `ISTART=0` (ou ligar LWAVE/LCHARG no Etot); com malha diferente o `ICHARG=1` não vale de qualquer forma.
- Stress do access/coaraci (`job.sh` com loop `05..50`): ao fim cada pasta `l` **não tem CONTCAR** (o script faz `mv CONTCAR POSCAR`); a estrutura final é o `POSCAR` da pasta (conferir com `finalpos` do `vasprun.xml`). `POSCAR_n` são as entradas de cada repetição. Etot parte desse `POSCAR`. (CaZrS3, 2026-11-11)
- Etot→DOS: o Etot do grupo sai com `WAVECAR`/`CHG` de 0 byte (`LWAVE/LCHARG=.FALSE.`); o DOS recomeça com `ISTART=0`.

## Estruturas do Materials Project sem chave (2026-11-11)
- O access não abre o site do MP (403) e a `mp_api` exige chave, mas o endpoint **OPTIMADE** responde sem chave:
  `curl "https://optimade.materialsproject.org/v1/structures?filter=elements HAS ONLY \"Ba\",\"Zr\",\"S\""` (URL-encode),
  com `lattice_vectors`, `cartesian_site_positions`, `species_at_sites` e `_mp_stability` (E acima da casca, r2SCAN/GGA).
- Pelo `urllib` do Python volta 403: mandar `User-Agent` explícito (ex. `curl/8`). Exemplo de uso:
  `~/work_vasp/BaZrS3/paw_pbe_1.125ENMAX_Etot/competing_phases/make_competing_phases.py` (fases concorrentes p/ Δμ).

## harpia: `--mem=0` é recusado pelo QoS (2026-11-11)
- `sbatch` com `#SBATCH --mem=0` (nó inteiro) falha com `QOSMaxMemoryPerJob`: o QoS `harpia_48a/48b` limita 48 G/job e a memória é 900 MB/CPU.
- Usar `--mem` = 900M × CPUs do job (48 CPUs → `--mem=43200M`; 16 CPUs → `--mem=14400M`), igual ao job `743`.
- Módulo VASP da harpia: `modmat/vasp/6.6.1-intel` (`vasp_std` + Intel MPI 2021.19). QoS: 1 job de 48 CPUs por partição (par48a/b), 16 em par16: jobs na mesma partição entram em sequência.

## VASP travado sem erro: watchdog de inatividade (2026-11-12, Ag2CrO4 fases concorrentes, coaraci)
- Jobs 1931613 (CrO3 l=15) e 1931621 (Ag2Cr2O7 l=50) ficaram TIMEOUT após 3 d, parados 55 h e 31 h: `ALGO=All`, `ISIF=3`, `ISTART=0`; DAV converge até o passo 8, `SDA:9` salta p/ E=+45/+86 eV (rms 626–1680) e o `saida` nunca mais cresce; `mpirun` vivo, sem erro. O gatilho STOPCAR de 60 min antes do fim não age em VASP travado.
- Correção padrão: `~/skills/global/job_watchdog.sh` (`run_watched`). Teste de ALGO (Normal/Fast, 4 runs de 12 ranks) em `chemical_potentials/_algo_test/`.
- Diagnóstico ao voltar: `ls -l --time-style=full-iso saida_*.out OSZICAR` vs hora do TIMEOUT; log de job sem linha nova por >1 h = travou, não "lento".

## Charge sloshing em óxidos com Nd: detector offline calibrado (2026-11-12, Ag2CrO4 fases concorrentes)
- Passos eletrônicos máx por passo iônico (OSZICAR_* das stress, ALGO=All): Nd2O3 mediana 119 (máx 127), NdCrO3 93 (96); sem Nd: CrO3 44, CrO2 35, AgCrO2 28, Cr2O3 20, Ag2O 17. Nenhum INCAR tinha `LMAXMIX` (Cr d → 4; Nd f → 6).
- `~/skills/global/scf_monitor.py`: `--calib OSZICAR...` (estatística) e `--check OSZICAR` (ciclo em andamento; exit 3 = sloshing). Critérios: (a) >60 passos, (b) sem melhora de 10× em min|dE| entre janelas de 20, (c) oscilação de sinal. Calibração em ~2100 ciclos convergidos: 0 falsos positivos em Ag2O/AgCrO2/Cr2O3/CrO2/CrO3, 1/308 em AgO, e dispara em 34/181 (Nd2O3) e 22–28/200 (NdCrO3) — ciclos que convergiriam só após 60–127 passos.
- NÃO pega o travamento do VASP (`SDA:9`, 9 passos e parado): esse é do `run_watched`. Teste de efeito do `LMAXMIX=6` (job 1937336, `_lmaxmix_test/`): resultado pendente.
