# Workflow CRYSTAL23 — etapa por etapa

Complemento do `SKILL.md`. Páginas citadas = páginas do manual; achar a linha pelo índice C de `CRYSTAL23_Manual.md` (`grep -n "p187:" CRYSTAL23_Manual.md`).

## 0. Anatomia do INPUT (d12) gerado por `cry_input.py`

```
<título>                         # linha 1, livre
CRYSTAL                          # bloco 1: geometria (p.19-24)
0 0 0                            # IFLAG IFHR IFSO (0 = grupo por número; setting padrão)
14                               # grupo espacial (número)
4.854 10.332 6.956 91.13         # só os parâmetros independentes do sistema cristalino (monoclínico: a b c β)
6                                # nº de átomos da UNIDADE ASSIMÉTRICA
247 0.2616 0.2481 0.5916         # Z convencional (Z+200 = base com ECP: 247 = Ag) + frações
...
OPTGEOM ... ENDOPT               # só em fullopt/atomopt (cap. 7)
END                              # fim do bloco 1
<bases>  99 0  END               # bloco 2 (ou BASISSET / POB-TZVP-REV2 no lugar do END + bloco 2)
DFT  <funcional>  [SPIN]  XXLGRID  ENDDFT     # bloco 3
SHRINK  IS ISP  |  0 ISP / IS1 IS2 IS3 + NOSYMADA
TOLINTEG 8 8 8 8 16   TOLDEE 8   FMIXING 30   MAXCYCLE 1500   BIPOSIZE/EXCHSIZE 40000000
[SPINLOCK] [LEVSHIFT] [GUESSP] [PPAN]
END
```
- **Arquivo `crygeo`** = as linhas de `CRYSTAL` até o último átomo, escritas à mão a partir da CIF (grupo + unidade assimétrica). Conferir no `crystal.out` (`NUMBER OF SYMMETRY OPERATORS`, lista `ATOMS IN THE UNIT CELL`) que o número de átomos bate. Setting não padrão / origem: ver IFHR/IFSO (p.19-20).
- **Geometria de etapa anterior:** `--geom runs/X/fort.34` → `EXTERNAL` (o script copia o `fort.34` para o run dir; o job o leva ao scratch). O `fort.34` traz célula primitiva, operações de simetria e átomos (formato p.450-451).
- **Base:** pob-TZVP-rev2 (`~/work_crystal/basis/<El>_pob-TZVP-rev2.basis`; Ag com ECP 28 → Z 247). Internas disponíveis por `BASISSET`: STO-3G/6G, POB-DZVP, POB-DZVPP, POB-TZVP, POB-DZVP-REV2, POB-TZVP-REV2 (Z 1–35, 37–53, 55–56, 72–84 no TZVP-rev2; p.28). Dependência quase linear e bases para iônicos: cap. 17.
- **TOLINTEG** (p.130): 5 limiares de truncamento das séries de Coulomb/troca (default 7 7 7 7 14). O usuário usa **8 8 8 8 16** (mais rígido; recomendado para híbridos e otimização de célula). Mudar só com teste.
- **Grade** (p.143-147): XLGRID é o default do CRYSTAL23; o usuário usa **XXLGRID**. Manter a mesma em todo o rito.

## 1. Convergência de k-points

```bash
python3 $S/cry_input.py --geom mat.crygeo --basis-dir basis --basis-tag pob-TZVP-rev2 --func <F> \
        --mode kconv --klengths "5 10 15 20 25 30 35 40" --name <f>_kconv [--cell-from X/crystal.out] [--kconv-opt]
for d in runs/<f>_kconv_l*; do sbatch $S/job_crystal.sh $d; done     # custo reportado antes!
python3 $S/cry_parse.py kconv runs/<f>_kconv_l* --csv kconv_<f>.csv
```
- **Funcional da série = funcional de produção** (a malha que satura em PBE costuma servir para o híbrido, mas o gap converge diferente; se for usar a malha PBE no híbrido, conferir 1–2 malhas com o híbrido).
- Malhas repetidas para l diferentes são puladas. Exemplo Ag2SeO3 (|b| = 0,206 / 0,097 / 0,144 Å⁻¹): l=10 → 2×1×1, 15 → 3×1×2, 20 → 4×2×3, 25 → 5×2×4, 30 → 6×3×4, 35 → 7×3×5, 40 → 8×4×6.
- **Critério (propor ao usuário):** ΔE ≤ 1 meV/átomo vs. a malha mais densa e gap estável (≤ 0,01 eV); com `--kconv-opt`, também ΔV ≤ 0,1 %. Escolher um ponto **no platô com folga**, nem o menor que passou nem o maior (mesma regra do VASP). Isolantes de gap largo saturam cedo (MgO PBE: 4×4×4 a 4,9 meV/át. de 6×6×6; 2×2×2 a 402 meV/át.).
- **SP × FULLOPTG por malha:** a série com SP na geometria inicial (experimental) é o padrão barato; `--kconv-opt` repete o rito do VASP ao pé da letra (ISIF=3 em cada l) — com híbrido em 24+ átomos isso são dias de máquina; só se o usuário pedir.

## 2. Escolha da malha
Apresentar a tabela (`kconv_<f>.csv`) e **perguntar**. Registrar no plano/cofre: malha, ISP, funcional, base, TOLINTEG, grade.

## 3. Stress — OPTGEOM + FULLOPTG (≈ VASP ISIF=3)

```bash
python3 $S/cry_input.py --geom mat.crygeo ... --func <F> --mode fullopt --k A B C --name <f>_fullopt
sbatch $S/job_crystal.sh runs/<f>_fullopt
python3 $S/cry_parse.py opt runs/<f>_fullopt/crystal.out
```
- Defaults (cap. 7): quasi-Newton BFGS, Hessiana inicial de Schlegel, trust radius; critérios TOLDEG 0,0003 (RMS gradiente) e 1,5× para o máximo, TOLDEX 0,0012 (RMS deslocamento) e 1,5× para o máximo; os 4 juntos fecham. `TOLDEE 8` no OPTGEOM (≥ SCF). `FINALRUN 4` (default): após convergir, reclassifica as integrais na geometria final, refaz energia+gradiente e reotimiza até ficar estável.
- Pressão: sem `EXTPRESS` = pressão zero (≠ CP2K, cujo default é 100 bar). `--extpress P` em **hartree/bohr³** (1 GPa = 3,3989×10⁻⁵ Ha/bohr³).
- Gradientes analíticos de célula/íons existem para HF, GGA e híbridos (globais e RSH), all-electron e ECP. Exceção: **SMEAR** (condutor) → gradiente analítico incompleto → `NUMGRALL`/`NUMGRATO` (2·N·custo SCF; p.196).
- Iônicos com Hessiana mal definida: `IONRAD` dentro do OPTGEOM (raios iônicos na Hessiana de Schlegel; p.192). É keyword do bloco OPTGEOM (o `--extra3` escreve no bloco 3): editar o INPUT à mão e registrar.
- Saídas: `fort.34` (geometria final; **só existe se convergiu**), `optcNNN` (geometria de cada passo, guardadas em `opt_steps/`), `OPTINFO.DAT` (restart), `HESSOPT.DAT` (Hessiana: pode iniciar outra otimização com `HESSOPT`), `fort.33` (trajetória xyz), `SCFOUT.LOG`.
- Conferir: célula final vs. inicial (Δa %, ΔV %) e vs. experimento; em PBE espera-se superestimar ~1–2 %; B3LYP/HSE06 costumam ficar mais perto.

### Restart de otimização (p.208)
1. **Interrompida (tempo, MAXCYCLE):** mesmo INPUT + `RESTART` no OPTGEOM (`cry_input.py ... --restart-opt`, mesmo `--name` ou copiar), com `OPTINFO.DAT` e `fort.9` no run dir (o job copia `fort.9 → fort.20` e o `OPTINFO.DAT`). `MAXCYCLE` continua contando do último passo + 1: aumentar.
2. **`TRUST RADIUS TOO SMALL` ou caminho ruim:** novo run partindo da última `opt_steps/optcNNN` renomeada para `fort.34` (`--geom .../optcNNN --geom-fmt fort34`).

## 4. Etot — OPTGEOM + ATOMONLY a partir do `fort.34` (≈ VASP ISIF=2)

```bash
python3 $S/cry_input.py --geom runs/<f>_fullopt/fort.34 ... --func <F> --mode atomopt --k A B C --name <f>_atomopt
```
- Mesma base/TOLINTEG/grade/malha da etapa 3. Átomos em coordenadas fracionárias simetrizadas; se não houver direção livre por simetria (ex. MgO), o CRYSTAL avisa e para: aí a etapa 4 vira um SP.
- Energia para comparações (defeitos, fases, μ): `OPT END - CONVERGED ... E(AU)` (`cry_parse.py check/opt`). Fases de referência/constituintes: **mesmo rito, mesma base, mesmo funcional e mesmo spin** (regra do VASP).

## 5. DOS e bandas (GGA e híbrido)

```bash
python3 $S/cry_input.py --geom runs/<f>_atomopt/fort.34 ... --func <F> --mode sp --k A B C --name <f>_sp
sbatch $S/job_crystal.sh runs/<f>_sp                                   # gera fort.9
python3 $S/cry_props.py --scf-out runs/<f>_sp/crystal.out --what both --path "..." | --path-frac "..."
sbatch -t 02:00:00 $S/job_crystal.sh runs/<f>_sp props
python3 $S/cry_parse.py bands runs/<f>_sp && python3 $S/cry_parse.py dos runs/<f>_sp
```
`PROPS` gerado (exemplo MgO, verificado):
```
BAND
band structure
5 8 400 1 29 1 0          # NLINE ISS NSUB INZB IFNB IPLO(1=fort.25+BAND.DAT) LPR66
0 0 0 4 0 4               # segmentos em unidades de 1/ISS dos vetores recíprocos (ISS=0 → rótulos "G X")
...
NEWK
12 24                     # IS ISP (3× a malha SCF; ISP = 2·IS); anisotrópica: "0 ISP" + "IS1 IS2 IS3"
1 0                       # IFE=1 (energia de Fermi; obrigatório com SPINLOCK/LEVSHIFT) NPR
DOSS
2 6001 1 29 2 18 0        # NPRO NPT INZB IFNB IPLO(2=DOSS.DAT) NPOL NPR
-1 1                      # projeção: -N átomos, seguidos dos índices (célula unitária, ordem do crystal.out)
-1 2
END
```
- **Ordem BAND → NEWK → DOSS** (p.310, p.320, p.346): BAND depois do NEWK destrói os autovetores (SABF).
- Janela de bandas: `--bands-below/--bands-above` em torno do HOMO (= elétrons/2 em camada fechada). Ela também define a janela de energia da DOS: incluir caroço dilui os 6001 pontos (o `cry_parse.py dos` avisa se o passo > 20 meV).
- NEWK com IS menor que o do SCF dá imprecisão na transformada de Fourier (p.346); nunca usar < malha SCF.
- **Caminho no BZ:** rótulos aceitos só os das Tabelas 14.1/14.2 (índice B). P monoclínico aparece com A, B, C, D, E, Y, Z (conferir a tabela, o texto do PDF embaralha as coordenadas); FCC só X, L, W (verificado: K dá erro). Fora disso, `--path-frac` com frações dos vetores **recíprocos primitivos** (o script calcula ISS = mmc dos denominadores).
- Saídas: `fort.25` (blocos `-%-` BAND/DOSS com E_F), `BAND.DAT`, `DOSS.DAT` (E−E_F em Ha; projeções e total por último). `cry_parse.py` converte para eV (`bands.csv`: E−E_F; `DOS_raw_data.csv`: estados/eV/célula).
- Gap: SCF imprime `DIRECT/INDIRECT ENERGY BAND GAP` a cada ciclo — **vale a última ocorrência** (rede SCF). O `bands` dá VBM/CBM e gap ao longo do caminho; relatar os dois e o k de cada extremo.
- **HF/híbrido:** autovalores HF puros não são energias de excitação (p.309-310); híbridos (HSE06/PBE0/B3LYP) são a escolha usual para gap. Para comparar com VASP-HSE06 usar HSE06 aqui (mesmo ω = 0,11 bohr⁻¹, 25 %).

## 6. Spin, magnetismo, convergência difícil

- **Spin:** `--spin` (SPIN no bloco DFT) + `--spinlock "NALPHA-NBETA NCICLOS"` para fixar o momento no início; momentos por átomo com `ATOMSPIN` (no bloco 3, via `--extra3`); edição da matriz de spin `SPINEDIT` (p.128). Comparar ordens magnéticas como no VASP. NEWK IFE=1 obrigatório depois.
- **SCF lento/oscilante:** subir `FMIXING` (30→50–70), `LEVSHIFT "5 1"` (0,5 Ha, travado) para isolantes, `BROYDEN` (p.100), `ANDERSON` (p.98); `SMEAR` só para metais (implica gradientes numéricos na otimização). Depois de convergir com LEVSHIFT, os autovalores ficam deslocados → NEWK IFE=1 nas propriedades.
- **Chute de densidade:** `--guessp` lê `fort.20` (o job copia o `fort.9` do run dir) — útil para trocar de funcional na mesma geometria (PBE → HSE06).
- **Dispersão:** DFT-D3 / gCP / métodos 3c no cap. 5 (índice B "DFT-D3"); decidir com o usuário antes de usar.

## 7. Custos de referência (para estimar antes de submeter)
Ver `gotchas.md` §2. Regra prática: custo ∝ (nº de k na IBZ) × (nº de AO)³ na diagonalização + séries de troca (híbrido) que crescem com TOLINTEG; RSH ~2–3× um híbrido global; usar a simetria reduz k na IBZ e integrais.
