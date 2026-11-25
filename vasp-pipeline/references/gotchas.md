# Armadilhas VASP e de dados

- **Núcleos ociosos no job (2026-10-30, access):** os 300 estáticos do rattle (job 4958027) pediam `--ntasks-per-node=4 --cpus-per-task=8` (32 cpus cobradas) mas `mpirun -np $SLURM_NTASKS` lançava só **4 ranks** (OUTCAR: `running 4 mpi-ranks`); o `vasp_std` não usa OpenMP, então 28 de 32 cpus ficaram paradas (4,1 h/frame, 131 núcleo-h cobrados, ~16 úteis). **Regra:** `ntasks × cpus-per-task` = cpus que o VASP realmente usa; conferir `running N mpi-ranks` no OUTCAR e `NumCPUs` no `scontrol`. Nós da access: `S:C:T 2:14:2`, 56 cpus = 28 núcleos físicos, **52 cpus úteis (`CPUEfctv`) = 26 núcleos**; `-n 56` é recusado (`Requested node configuration is not available`). Receita sem ocioso: 1 rank por núcleo físico, `--ntasks-per-node=24 --cpus-per-task=2`, `OMP_NUM_THREADS=1`, `I_MPI_PIN_DOMAIN=core`; INCAR `KPAR × NCORE = ntasks` com KPAR dividindo NKPTS (16 k-pontos: KPAR=8, NCORE=3). Antes de arrays grandes: 1 frame-teste e comparar tempo.

- **access `vasp/6.4.3` = Open MPI 5 (conda), não Intel MPI (2026-11-19):** `--cpus-per-task=1` em nó com hyper-threading → Open MPI aborta com `A request was made to bind ... more cpus than are available` e o laço do `bash_stress.sh` seguia 50× com `cp: cannot stat 'CONTCAR'`. Correção: `--ntasks-per-node=24 --cpus-per-task=2`, `OMP_NUM_THREADS=1`, `mpirun --map-by core --bind-to core`, e abortar o laço se `rc≠0` ou sem `CONTCAR`/`OSZICAR`.
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
- **LAMMPS+DeePMD do pip na coaraci (2026-11-17):** env `deepmd_md` (deepmd-kit 3.1.3, `lammps` 2025.7.22 wheel): o executável `lmp` sai com rc 245 (segfault) sem saída, até em `lmp -h`; o job acusa só `LMP_FALHOU`. A API Python roda o mesmo input (`from lammps import lammps; l=lammps(cmdargs=['-log','log.lammps']); l.file('in.x')`), `pair_style deepmd g1..g4 out_freq 10 out_file model_devi.out` ok. Wrapper: `work_vasp/BaZrS3/md_AL3_val/run_lmp.py`. CPU, 80 át., se_e2_a rcut 6, 4 modelos: ~8,6 passos/s com 4 threads.

## `COMPLETED` do SLURM não prova VASP ok (2026-10-31, BaZrS3 QbC coaraci)
- Loop de pastas em um job: se faltar POSCAR/KPOINTS, o VASP aborta ("I REFUSE TO CONTINUE") em segundos e o job sai `COMPLETED` rc 0 (~10 min/job em vez de horas).
- Antes do `sbatch`: `ls */POSCAR */KPOINTS | wc -l` = nº de pastas. No loop: `rc=$?` logo após o `mpirun` (não dentro de `$(date)`) e marcar OK/FALHA por `grep -q '</modeling>' vasprun.xml`. Ao voltar: contar vasprun >1 KB, não ler só `sacct`.

## O pulo do stress (2026-11-09, Ag2CrO4:Nd) — NUNCA repetir
Ao montar Nd2O3, Ag2O e Cr2O3 (referências de μ) o assistente escolheu malhas k à mão (9×9×6, 9×9×9, 8×8×8) e partiu de ISIF=3 + ISIF=2 sem a convergência de k-points; dois jobs foram submetidos (1910439, 1911421) e cancelados ainda pendentes. Correto: passo 1 do rito (stress com `Auto` `l=05…50`, ISIF=3, 2×ENMAX, repetição até uma linha `F=`), tabela de convergência, usuário escolhe a malha, só então Etot (ISIF=2, 1.125×ENMAX). Também: Nd/O dos `pure_athoms` ficaram com `ISPIN=1` enquanto as células dopadas são `ISPIN=2` (diferença de 0,75 eV/átomo de Nd no μ).
- **TDOS do DOSCAR dividido por 800 (2026-11-07, Ag2CrO4):** 6 dos 7 complexos de 222 átomos (VASP 6.6.0, build de 08/04/2026) têm o bloco total do `DOSCAR` em escala 1/800 constante (integral em E_F = 2,056 em vez de NELECT = 1645; razão DOSCAR/`vasprun.xml` 799,6–800,4 em todas as energias). O `vasprun.xml` e o PDOS por átomo estão certos; o build de 19/08 não tem o fator 1/800, mas (2026-11-19, set2 `E332v4`, 9 células com `NUPDOWN = 3`) grava o TDOS **e o PDOS** ×2 (integral até o VBM ≈ 3290 = 2×NELECT; PDOS integra acima de NELECT, impossível dentro das esferas PAW) — não verificado se é do build ou do NUPDOWN. **Regra:** antes de usar o TDOS do DOSCAR, conferir a integral em E_F contra o `NELECT` do OUTCAR (o `plot_dos_per_atom.py` da `vasp_plot` faz e reescala com aviso; desde 11-19 reescala também o PDOS se ele integrar > NELECT); gap ou figura tirados do total desses DOSCAR sem conferir saem errados.
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

## Metais (ZrS, Zr3S4, ZrS2) e scancel (2026-11-12)
- Stress com ISMEAR=0/σ=0,01 oscila ±3 meV/átomo com l; com ISMEAR=1/σ=0,1 (`_MP01`) cai a ≤1 meV/átomo em l≥35–40 mas não zera. Escolher l no trecho estável e Etot com ISMEAR=1 σ=0,1 (reportar energy sigma->0). l=50 pode ser outlier (volume salta em ZrS2, vdW).
- Antes de `scancel`+reenvio em outra partição, conferir `sacct`: job curto pode já ter terminado (808 mp9179 terminou em 7 min e o reenvio repetiu o cálculo).

- **2026-11-12 (BaZrS3) — μ elementares em outra escada de ENCUT:** `pure_athoms/*_OK` rodados a 528 eV (stress 1056, ENMAX de outro estudo) enquanto hospedeiro, supercélulas e fases concorrentes estavam a 389,66 (1.125×346,364). O paper afirmava "same parameters". Antes de qualquer ΔH_f/E_f: `grep 'ENCUT  =' */OUTCAR` em TODAS as referências e conferir que é o mesmo número do hospedeiro (e o mesmo ISPIN/POTCAR). E_b de complexos não depende de μ; ΔH_f, polígono e E_f com ΔN≠0 dependem.
- **2026-11-13 — Slurm `COMPLETED` não prova convergência; checar `F=` no OSZICAR.** Ag2CrO4:Nd 2V_Ag set2 (222 at.), `ALGO=Normal` do zero: 1ª leva 1933995–99 e 2ª 1937828–36 divergiram (TT_NN 1937829: E→−1e9 eV, parou no NELM=200, 0 linhas `F=`, exit 0, ~1700 núcleo-h). Nd exige `ALGO=All` (4f). Ressubmetidos 1938698–706 com `ALGO=All`; atenção ao OOM do gotcha de 2026-11-08 (SDA em >200 at.) — conferir MaxRSS dos primeiros passos.
- **2026-11-17 — `ALGO=Normal` diverge no set2 (Nd, 222 at.) MESMO com Kerker e CHGCAR real** (E332v2 `1947636`, ICHARG=1, BMIX=1.0 AMIX 0,2 AMIX_MAG 0,8): delay limpo até −1353,4 e divergência PARA BAIXO no 1º passo de mistura (rms(c) 0,02→0,49, −3531 eV no SCF 19). 4ª falha do Normal nesse sistema; só `Fast` foi estável. Não usar Normal em células com Nd, nem como "etapa só p/ WAVECAR".

## EDWAV `gradient is not orthogonal` (rot.F:874) com ALGO=All (2026-11-14, Ag2CrO4:Nd 222 at., 1645 e)
- Causa (wiki Known issues #111, aberto desde 6.1.0): ALGO=All partindo de carga atômica/sem WAVECAR perde a ortonormalidade no delay (NELMDL); o 1º passo CG acusa pelo teste ABSOLUTO 1E-4. Erro cai no fim do delay (SCF 5 com NELMDL=-5, SCF 12 com -12; Damped idem).
- NÃO resolvem: NCORE, ALGO=Damped, EDIFF=1E-4, NELMDL=-30 (diverge p/ baixo dentro do delay). Sinal precoce: E do delay estabiliza (~−1809) e depois deriva (−1843…−2076), nº de elétrons ≠ NELECT, M deriva.
- Padrão SAUDÁVEL: delay monótono; 1º passo CG SALTA PARA CIMA (+544 eV) e volta ao mínimo em ~15–100 passos (Nd convergidos partiram de CHGCAR/WAVECAR reais, E inicial ≈ −1788). Trava `E<-3000` só vale p/ divergência PARA BAIXO no delay; nunca matar por salto para cima.
- Também ocorre na RELAXAÇÃO a partir de WAVECAR bom (2026-11-14, job 1940006): All convergiu o 1º passo iônico (26 it, 12 min, E igual ao ponto único) e abortou no 1º SCF do passo iônico 2 (`1 1 1.068e-4`, teste absoluto 1E-4). WAVECAR bom não basta com All; no ponto único o Fast passou.
- Detalhe e canários: cofre `02_Memory/vasp/ag2cro4.md` e `…/vacancies_set2/PLANO.md`.

## CHGCAR editado à mão: preservar largura fixa dos campos (2026-11-18)
Ao modificar um CHGCAR (ex.: inverter a magnetização), manter a largura de cada campo (grade E17.11, ocupações de augmentation E15.7). Reescrever com `' '.join` desalinha as colunas; o VASP 6.6 lê as ocupações em formato fixo, o rank de I/O cai num ramo de erro e o job TRAVA em deadlock MPI (239 ranks em `MPI_Bcast`, 1 em `MPI_Allreduce`) logo após "initial charge density was supplied", sem nenhum passo SCF. Conferir: mesmo nº de bytes e mesmo comprimento de linha do original. Script certo: `~/work_vasp/Ag2CrO4/tools/flip_chgcar_mag.py`. Caso: Ag2CrO4 E332v4 `1948216`.

## Loop de relaxação ISIF=3 (2026-11-18)
- Critério "DONE = 1 passo iônico + reached accuracy" em loop CONTCAR→POSCAR pode nunca fechar: célula oblíqua/shear mole alterna entre 2 celulas (Ag2Cr2O7 l=10, job 1943627: 18 runs, ~2 d, E alternando -146.396/-147.22 eV, V const, stress ~0.1 kB). Todo loop de restart deve ter limite de runs (ex.: ≤6) e/ou detectar E alternante → FAILED; olhar `grep -c 'F=' OSZICAR_*` e a energia por run antes de esperar.

- (2026-11-18) ICHARG=1 com LCHARG=T: o CHGCAR de entrada é SOBRESCRITO pela rodada (mesmo falha). Guardar cópia do CHGCAR de entrada (ou usar outro nome/pasta) antes de reenviar; senão regenerar da fonte (ex.: E332v4/TO_NF 1948380 → reenviado 1948876). Mistura instável (rms(c) crescendo, ZHEGV em EDDRMM) em 1 config enquanto as irmãs convergem: baixar AMIX/AMIX_MAG antes de subir NELM.

- (2026-11-19) SCF com `ALGO=Fast` no set2 (Ag2CrO4:Nd, 112 at.) pode, depois de ~90 passos bons (rms(c) ~2e-4), DIVERGIR para um estado espúrio estável: E sobe ~0,4 eV e rms(c) fica CONSTANTE (6,62e-2 por >25 passos) — não oscila de volta. O guard de `job.sh` (E<−3000) não pega (é para cima) e o job queima o `-t` inteiro (TO_NF 1948876: TIMEOUT 6 h × 240 núcleos). Sinal de alerta: rms(c) idêntico em várias leituras e E acima do patamar anterior; matar e reenviar. Não confundir com o padrão benigno do TT_NN (rms(c) sobe devagar em ciclos de ~25 passos e depois cai de uma vez; convergiu no passo 151): o que distingue é rms(c) CONSTANTE vs. variando.

- (2026-11-19) `NUPDOWN` fixo: o OUTCAR traz DOIS `Fermi energy:` (um por canal de spin, ordem NÃO confiável) e o `E-fermi`/DOSCAR é só um deles; dentro de um gap o E_F de cada canal é arbitrário. Para PDOS/gaps de células com M fixo referenciar ao VBM/CBM de cada canal (EIGENVAL, occ>0.5), nunca ao E_F do DOSCAR (Ag2CrO4:Nd, set2: E_F−VBM variou de −0,7 a +0,95 eV entre canais). Sem NUPDOWN (M livre, canal único) E_F≈VBM+0,045 eV vale.
- (2026-11-19) Preparar relaxação a partir de CHGCAR de outra pasta: copiar de verdade (`cp`), nunca `ln` (hard link): o VASP regrava o CHGCAR no mesmo inode e destrói o arquivo de origem.

## 2026-11-19 — Guardar o WAVECAR do SCF convergido; regenerar por ICHARG=11 (Ag2CrO4:Nd, set2 3×3×2)
- Rodadas "estáticas" convergidas com `LWAVE=.FALSE.` (E332v4) deixaram só o CHGCAR; o relax seguinte (v5, ISTART=0 + NELMDL=−8) caiu em estado espúrio/sloshing (F 0,35 eV acima do estático convergido; 2 jobs × 4 h × 240 núcleos perdidos). Em SCF difícil (Nd-4f, ISPIN=2), **manter `LWAVE=.TRUE.` na etapa estática** que vai alimentar um relax.
- Se o WAVECAR faltar: etapa não-SC barata (`ICHARG=11`, `ISTART=0`, `NSW=0`, `ALGO=Normal`, `LWAVE=.TRUE.`) sobre o CHGCAR convergido gera os autoestados em minutos; depois o relax com `ISTART=1`/`ICHARG=1`. WAVECAR de outra malha k (ex. Γ) não serve.
- ALGO=Fast com BMIX=0,0001 (sem Kerker) é a única receita estável no set2, mas lenta (100–150 SCF); Normal/Kerker explodiu 4×. Teste do ALGO=All + WAVECAR: ver nota ag2cro4 (job 1950391).
- (2026-11-20) **Nd 4f (LMAXMIX=6, NUPDOWN fixo): várias soluções SCF estáveis na MESMA geometria.** Ag2CrO4:Nd set2 TT_NN, receita idêntica (Fast, BMIX=1e-4, NELMDL=-8 sobre o mesmo CHGCAR): F = −1353,34 / −1353,68 / −1353,97 eV conforme as ondas aleatórias iniciais. Numa relaxação, queda de F de ~0,3–0,6 eV entre passos iônicos com forças de 0,1 eV/Å é TROCA DE ESTADO eletrônico (desejável), não sloshing — o v5 1950285 foi cancelado por esse erro. Não cancelar por rms(c) subindo nem por queda de F; só se F SUBIR entre passos ou divergir. Consequência: energia de ponto único de célula com Nd pode ser de estado metaestável; comparar configurações só depois de relaxar/reconvergir de mais de um ponto de partida. Relax com Nd: NELM alto (1500), senão o passo iônico sai com forças de SCF não convergido. ALGO=All com WAVECAR vazio + sem NUPDOWN → EDWAV rot.F:874 (1950936).

## 2026-11-21 — STOPCAR/LABORT: o VASP apaga o STOPCAR ao parar
- Job que resubmete "se STOPCAR existir" após `LSTOP`/`LABORT` nunca resubmete: o VASP imprime "deleting file STOPCAR". Usar arquivo-flag próprio (`touch STOPPED` junto do STOPCAR; testar `[ -f STOPPED ]`) — v7 1950944 saiu FAILED por isso (E332v7_relax/TT_NN).
- SCF do primeiro passo iônico sem convergir não se resolve esperando: guard `>400 SCF sem "F=" no OSZICAR → FAILED` (1950944 gastou 17 h × 240 núcleos em 1034 SCF oscilando).

- (2026-11-22) Guard de SCF precisa valer em TODO passo iônico, não só no 1º: contar DAV/RMM desde o último `F=` (`awk '/F=/{n=0} /^(DAV|RMM|DMP)/{n++} END{print n+0}' OSZICAR`, >400 → matar + FAILED). Com `! grep -q 'F='` o 6º passo do TT_NN (1951438) derivou 937 it. e queimou 20 h × 240 núcleos; o STOPCAR por tempo só é lido no fim do passo iônico, então não salva SCF preso.

## EDWAV rot.F:874 provavelmente é do BUILD, não do ALGO=All (2026-11-24, coaraci)
- `vasp660/bin/vasp_std` (grupo lcabral) foi REGRAVADO em 2026-08-19 (cabeçalho: `build Aug 19 2026 13:19:26`; o de `Apr 08 2026` sumiu). 21 runs ALGO=All de 05–08/2026 (build abril, incl. do zero em 112 at.) sem EDWAV; build agosto: 24/24 tentativas de nov. com EDWAV (222 at. Nd). `ldd`: o novo linka `libblas/liblapack.so.3` 3.12.0 e `libscalapack.so` de `/home/sw/netlib/intelmpi-2021.9` (ref. netlib, 19/08 12:38), não MKL. Conferir sempre `head -1 OUTCAR` ao comparar runs.
- `/home/sw/vasp/6.5.0-intel/bin/vasp_std` não é módulo e exige `libscalapack.so.2` inexistente: shim `ln -s $MKLROOT/lib/intel64/libmkl_scalapack_lp64.so.2 shim/libscalapack.so.2` + `LD_PRELOAD=libmkl_blacs_intelmpi_lp64.so.2`. Canário: job 1958409.
- Harpia (`modmat/vasp/6.6.1-intel`): nó único 128 CPU/118 GB, ver cofre running_jobs.

- **Guard de SCF/OSZICAR lendo arquivo velho (2026-11-25, ag2cro4 TT_NN, job 1952057):** o guard de job (`>400 it.` em OSZICAR) rodou no 1º minuto sobre o OSZICAR da corrida anterior (ainda não reescrito) e matou o VASP em 63 s com 0 passos iônicos (240 núcleos, 20 h reservadas). Todo job com guard sobre OSZICAR/OUTCAR deve arquivar o arquivo antigo no início (`[ -s OSZICAR ] && mv OSZICAR OSZICAR.prev_$SLURM_JOB_ID`) antes de iniciar o guard.
