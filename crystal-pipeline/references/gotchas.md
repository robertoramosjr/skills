# CRYSTAL23 — fatos verificados e armadilhas

Cada item tem data e fonte (run real ou página do manual). Lição nova entra aqui, com data.

## 1. Máquina (harpia)

- `module load modmat/crystal/23.1.0.1` → `CRY23_ROOT=/home/hpc/software/crystal/23.1.0.1`. Binários: `bin/Linux-ifort_i64_omp/v1.0.1/{crystalOMP,PcrystalOMP,properties,Pproperties}` e `bin/Linux-ifort_i64/v1.0.1/{crystal,Pcrystal,properties,Pproperties}` (2026-11-17).
- Precisa de `export LD_LIBRARY_PATH=/opt/intel/oneapi/compiler/2026.2/lib:$LD_LIBRARY_PATH` (runtime Intel), herdado do `~/work_crystal/scripts/job_crystal.sh` do usuário (2026-11-17).
- RAM 900 MB/CPU (`DefMemPerCPU=900`): 48 CPUs → `--mem=43200M`. Partição `par48a`, até 3 d.
- **Topologia (2026-11-17):** 1 nó, 2 sockets × 32 núcleos × 2 hyperthreads = 128 CPUs Slurm; NUMA0 = CPUs 0-31,64-95, NUMA1 = 32-63,96-127. `CR_CPU_MEMORY` + `task/cgroup,task/affinity`: o Slurm aloca **pares de hyperthreads de núcleos inteiros** (48 CPUs → 24 núcleos físicos; cpusets vistos: `0-23,64-87`, `32-55,96-119`). QoS 48a/48b: 48 CPUs e 48 GB por usuário. Ou seja, o job 876 (`-c 48`, 48 threads) rodou em **24 núcleos com 2 threads cada**, não em 48 núcleos: a razão TCPU/TELAPSE ≈ 46,7 conta hyperthreads.
- **Benchmark de layout (jobs 879/893, ~1 h de 24 núcleos):** crystalOMP 48 threads é o mais rápido no SCF (208 s) contra 229 s com 24 threads (HT dá ~10 %), 226 s no híbrido 24×2, 251 s com 24 ranks MPI, 264 s com 48 ranks; no SCF completo + 1 gradiente: OMP-48 667 s, híbrido 711 s, MPI-24 1094 s (gradiente máx. idêntico, 0,045424). Inputs e saídas em `~/work_crystal/bench_parallel/`.
- `Pcrystal`/`PcrystalOMP`/`Pproperties` estão linkados com OpenMPI (`libmpi.so.40`), que o módulo não carrega: usar `/home/hpc/software/openmpi/4.1.8-orca` (4.1.8, gfortran, com `plm/ras slurm`). Testado: MgO 4 ranks, energia idêntica à serial. OpenMPI 5 (`/usr/lib64/openmpi`, ohpc) não testado.
- OpenMP: `OMP_PLACES=threads` ou `cores` com 48 threads dão o mesmo binding efetivo (thread i → par `{i, i+64}` ou hyperthread individual) e o mesmo tempo.

## 2. Tempos medidos

| Sistema | Nível | Malha (IBZ) | Recursos | Tempo | Fonte |
|---|---|---|---|---|---|
| Ag2SeO3, 24 at., **P1**, 660 AO, 384 e⁻ | B3LYP, pob-TZVP-rev2 (Ag ECP), XXLGRID, TOLINTEG 8 8 8 8 16 | 3×3×3 (14) | 48 thr | SP: 1583 s, 13 ciclos SCF | job 876, 2026-11-17 |
| idem | idem, FULLOPTG | 3×3×3 | 48 thr | 2 pontos em 54 min (cancelado; ponto 1: grad. máx 0,038, RMS 0,010 vs limiares 0,00045/0,0003) | job 877 |
| MgO, 2 at., Fm-3m | PBE, POB-DZVP-REV2, XLGRID, TOLINTEG 7 7 7 7 14 | 2/4/6 (3/8/16) | 2 thr | SP ~4 s cada; FULLOPTG 4 pontos 23 s; PBE0 SP 20 s | teste skill, 2026-11-17 |
| TiO2 rutilo, 6 at. | PBE, POB-DZVP-REV2 | 3×3×4 | 4 thr | **P4₂/mnm** (16 op., 9 k) ATOMONLY 5 pontos 92 s × **P1** (1 op., 19 k) SP 136 s | teste skill, 2026-11-17 |

Ag2SeO3 B3LYP k333: E = −11683,685146661 Ha, gap indireto 3,9135 eV (última linha de gap do SCF). O riper (TURBOMOLE) dá gap 3,97 eV com outra base; energias totais entre códigos/bases/ECP **não** são comparáveis.

## 3. Armadilhas verificadas

1. **`run_watched` perdia o stdin** (2026-11-17, **corrigido no `global/job_watchdog.sh`**): o watchdog rodava `setsid "$@" &`; em bash não interativo, comando em background recebe `/dev/null` como stdin, e `run_watched crystalOMP < INPUT` terminava na hora com `ERROR **** INPUT **** END OF DATA IN INPUT DECK`. Agora é `setsid "$@" <&0 &` (testado: stdin chega, travamento ainda mata com rc 124). Valia para qualquer programa que lê do stdin.
2. **Rótulos de BAND** (2026-11-17): `ERROR **** BANDE **** UNKNOWN K-POINT SYMBOL` ao pedir `K` em FCC. Só os rótulos das Tabelas 14.1/14.2 existem → `--path-frac`.
3. **`DOSS.DAT`** (2026-11-17, MgO): cabeçalho `# NEPTS 6003 NPROJ 3 NSPIN 1`, eixo `E-EFERMI (HARTREE)` (já relativo a E_F), colunas = projeções na ordem do PROPS e **total por último** (soma conferida). NPT=6001 aceito (vira 6003 pontos).
4. **`fort.25`** BAND: cabeçalho `-%-0BAND   29   98 0.00000E+00 8.12012E-03-2.02766E-01` = IHFERM, NBAND, NKP, (DUM), DK, E_F em campos fixos (A3,I1,A4,2I5,3E12.5); números negativos colam (parsear por largura 12, nunca por espaço).
5. **Gap no SCF** é impresso a cada ciclo: usar a **última** ocorrência.
6. **Anisotropic SHRINK + simetria** (2026-11-17, TiO2 3×3×4 com 16 op.): roda com `NOSYMADA` (o manual p.125 diz que rede anisotrópica não é compatível com SABF).
7. **`fort.34` só existe se a otimização convergiu**; no meio do caminho, usar `optcNNN`/`optaNNN` (renomear para `fort.34`, keyword EXTERNAL).
8. **POSCAR → P1** perde simetria: TiO2 gastou 19 k na IBZ em vez de 9 e mais integrais. Sempre preferir `crygeo` com grupo espacial.
9. `sacct COMPLETED`/rc 0 não provam nada: o `properties` saiu com rc 0 mesmo com `ERROR **** BANDE ****` (2026-11-17). Validar por `EEEEEEEEEE TERMINATION` + `SCF ENDED - CONVERGENCE` (+ `OPT END - CONVERGED`).
10. O CRYSTAL **sobrescreve** a saída (o job redireciona para `crystal.out`): o `job_crystal.sh` renomeia o anterior para `crystal.out.<data>` antes de rodar.

## 4. Do manual (não testado aqui; conferir antes de depender)

- Default de otimização no CRYSTAL23 = FULLOPTG (até o CRYSTAL09 era só átomos); `FINALRUN 4` default (p.195, p.207).
- Optimização com SMEAR: gradiente analítico incompleto; com smearing ~0,001 Ha ainda serve (p.188).
- RSH (HSE06, HSEsol, LC-ωPBE...): sem expansão bipolar na troca, integrais em modo direto, custo 2–3× (p.138).
- Rede de Gilat: ISP efetivo = IS·NINT(MAX(ISP,IS)/IS) (p.125). O manual (p.126) diz que o código aceita 413 k na rede de Monkhorst e 2920 na de Gilat (frase possivelmente antiga); conferir se usar malhas muito densas.
- NEWK com IS menor que o do SCF → imprecisão na Fourier F_g → F_k (p.346).
- HF/híbrido: autovalores HF não aproximam bem excitações ópticas (p.309-310).

## 5. Bandas (2026-11-17)

- **Gap no caminho ≠ gap da rede SCF.** Ag2SeO3 B3LYP k333: rede 3,9135 eV, caminho Setyawan–Curtarolo 3,845 eV (VBM em M1–A, fora da malha 3×3×3). A banda de valência passa 0,07 eV acima do E_F impresso (que vem da rede SCF). Um parser que decide "ocupada se max(E) ≤ E_F" erra (deu gap −0,52 eV na 1ª versão); o certo é "banda de condução = primeira inteiramente acima de E_F".
- `fort.25` com ISS grande imprime as coordenadas do segmento em I5 (não 6I3): pular o 3º registro por linha, não por largura.
- ISS = 1800 é aceito pelo `properties` (pontos irracionais do monoclínico aproximados com erro 5×10⁻⁵).
