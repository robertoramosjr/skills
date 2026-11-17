# CRYSTAL23 — fatos verificados e armadilhas

Cada item tem data e fonte (run real ou página do manual). Lição nova entra aqui, com data.

## 1. Máquina (harpia)

- `module load modmat/crystal/23.1.0.1` → `CRY23_ROOT=/home/hpc/software/crystal/23.1.0.1`. Binários: `bin/Linux-ifort_i64_omp/v1.0.1/{crystalOMP,PcrystalOMP,properties,Pproperties}` e `bin/Linux-ifort_i64/v1.0.1/{crystal,Pcrystal,properties,Pproperties}` (2026-11-17).
- Precisa de `export LD_LIBRARY_PATH=/opt/intel/oneapi/compiler/2026.2/lib:$LD_LIBRARY_PATH` (runtime Intel), herdado do `~/work_crystal/scripts/job_crystal.sh` do usuário (2026-11-17).
- RAM 900 MB/CPU (`DefMemPerCPU=900`): 48 CPUs → `--mem=43200M`. Partição `par48a`, até 3 d.
- crystalOMP (1 processo × 48 threads) rodou o SP do Ag2SeO3 com TCPU/TELAPSE = 73962/1583 ≈ 46,7 threads efetivas: o OpenMP escala bem nesse tamanho (2026-11-17, job 876).
- `PcrystalOMP`/`MPPcrystal`: não testados (cap. 15 do manual).

## 2. Tempos medidos

| Sistema | Nível | Malha (IBZ) | Recursos | Tempo | Fonte |
|---|---|---|---|---|---|
| Ag2SeO3, 24 at., **P1**, 660 AO, 384 e⁻ | B3LYP, pob-TZVP-rev2 (Ag ECP), XXLGRID, TOLINTEG 8 8 8 8 16 | 3×3×3 (14) | 48 thr | SP: 1583 s, 13 ciclos SCF | job 876, 2026-11-17 |
| idem | idem, FULLOPTG | 3×3×3 | 48 thr | 2 pontos em 54 min (cancelado; ponto 1: grad. máx 0,038, RMS 0,010 vs limiares 0,00045/0,0003) | job 877 |
| MgO, 2 at., Fm-3m | PBE, POB-DZVP-REV2, XLGRID, TOLINTEG 7 7 7 7 14 | 2/4/6 (3/8/16) | 2 thr | SP ~4 s cada; FULLOPTG 4 pontos 23 s; PBE0 SP 20 s | teste skill, 2026-11-17 |
| TiO2 rutilo, 6 at. | PBE, POB-DZVP-REV2 | 3×3×4 | 4 thr | **P4₂/mnm** (16 op., 9 k) ATOMONLY 5 pontos 92 s × **P1** (1 op., 19 k) SP 136 s | teste skill, 2026-11-17 |

Ag2SeO3 B3LYP k333: E = −11683,685146661 Ha, gap indireto 3,9135 eV (última linha de gap do SCF). O riper (TURBOMOLE) dá gap 3,97 eV com outra base; energias totais entre códigos/bases/ECP **não** são comparáveis.

## 3. Armadilhas verificadas

1. **`run_watched` perde o stdin** (2026-11-17): o watchdog global roda o comando com `setsid ... &`; em bash não interativo, comando em background recebe `/dev/null` como stdin, e `run_watched crystalOMP < INPUT` termina na hora com `ERROR **** INPUT **** END OF DATA IN INPUT DECK`. Correção: `run_watched bash -c '"$0" < INPUT' "$BIN/crystalOMP"`. Vale para qualquer programa que lê do stdin (TURBOMOLE `define`, `properties`...).
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
