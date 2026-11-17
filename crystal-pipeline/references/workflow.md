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
- **Arquivo `crygeo`** = as linhas de `CRYSTAL` até o último átomo (grupo + unidade assimétrica). Gerar com `cry_symm.py` (spglib) a partir de POSCAR/CIF/P1, com `--verify` (o CRYSTAL reconstrói a célula com TESTGEOM e o script compara volume, composição e distâncias): `~/micromamba/envs/render_env/bin/python $S/cry_symm.py POSCAR -o mat.crygeo --verify`. Conferir no `crystal.out` (`NUMBER OF SYMMETRY OPERATORS`, lista `ATOMS IN THE UNIT CELL`) que o número de átomos bate. Setting não padrão / origem: ver IFHR/IFSO (p.19-20).
- **Geometria de etapa anterior:** `--geom runs/X/fort.34` → `EXTERNAL` (o script copia o `fort.34` para o run dir; o job o leva ao scratch). O `fort.34` traz célula primitiva, operações de simetria e átomos (formato p.450-451).
- **Base:** pob-TZVP-rev2 (`~/work_crystal/basis/<El>_pob-TZVP-rev2.basis`; Ag com ECP 28 → Z 247). Internas disponíveis por `BASISSET`: STO-3G/6G, POB-DZVP, POB-DZVPP, POB-TZVP, POB-DZVP-REV2, POB-TZVP-REV2 (Z 1–35, 37–53, 55–56, 72–84 no TZVP-rev2; p.28). Dependência quase linear e bases para iônicos: cap. 17.
- **TOLINTEG** (p.130): 5 limiares de truncamento das séries de Coulomb/troca (default 7 7 7 7 14). O usuário usa **8 8 8 8 16** (mais rígido; recomendado para híbridos e otimização de célula). Mudar só com teste.
- **Grade** (p.143-147): XLGRID é o default do CRYSTAL23; o usuário usa **XXLGRID**. Manter a mesma em todo o rito.

## 1. Convergência de k-points — mesmo padrão do VASP (stress por malha)

O rito do VASP (`bash_stress_coaraci.sh` + `extract_stress_data.py`, repo `robertoramosjr/VASP`, `scripts/`): uma pasta por comprimento `l = 05…50` (passo 5) do `KPOINTS Auto`, **ISIF=3 completo em cada uma**, todas em sequência num único job que se ressubmete quando faltam < 90 min; tabela `dados_convergencia_final.csv` (Kdensity, Kmesh, Lattice_Param, Energy, Pasta). No CRYSTAL:

```bash
python3 $S/cry_input.py --geom mat.crygeo --basis-dir basis --basis-tag pob-TZVP-rev2 --func <F> \
        --mode kconv --name <f>_stress_kconv [--cell-from X/crystal.out]   # -> runs/<f>_stress_kconv/05 … /50
sbatch $S/job_crystal.sh runs/<f>_stress_kconv                            # custo reportado antes!
python3 $S/cry_parse.py kconv runs/<f>_stress_kconv                        # -> dados_convergencia_final.csv
```
- Cada pasta é um **FULLOPTG** (célula + íons). O "repetir o ISIF=3 até o OSZICAR ter uma única linha `F=`" do VASP existe para reconstruir a base de ondas planas; no CRYSTAL a base segue os átomos e o equivalente embutido é o `FINALRUN 4` (default: reclassifica as integrais na geometria final e reotimiza até ficar estável).
- Malhas que se repetem para `l` diferentes **não são recalculadas** (entrada idêntica → resultado idêntico); ficam em `kmesh_map.txt` e entram na tabela como `(= ll)`.
- O job percorre as pastas em ordem, pula as convergidas, reinicia a otimização interrompida (`RESTART` + `OPTINFO.DAT` + `fort.9→fort.20`) e se ressubmete (margem 90 min, como no VASP). Reenviar o mesmo comando é seguro.
- **Funcional da série = funcional de produção**: o rito é feito com cada funcional (decisão do usuário, 2026-11-17).
- Exemplo Ag2SeO3 P2₁/c (|b| = 0,206 / 0,097 / 0,144 Å⁻¹): 05 → 1×1×1, 10 → 2×1×1, 15 → 3×1×2, 20 → 4×2×3, 25 → 5×2×4, 30 → 6×3×4, 35 → 7×3×5, 40 → 8×4×6, 45 → 9×4×6, 50 → 10×5×7.
- **Critério (propor ao usuário):** ΔE ≤ 1 meV/átomo e ΔV ≤ 0,1 % vs. a malha mais densa, gap estável; escolher um `l` **no platô com folga**, nem o menor que passou nem o maior (mesma regra do VASP).
- `--kconv-sp` (só single points na geometria inicial) existe para triagem barata, mas **não é o rito**.

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

Equivalência com o VASP: o SCF na geometria da etapa 4 faz o papel do estático que gera o `CHGCAR`/`WAVECAR` (aqui, `fort.9` = matriz de Fock/densidade convergida); **as bandas não são um single point**: são autovalores ao longo do **caminho de alta simetria** (= `ICHARG=11` com `KPOINTS` em line-mode), e a DOS é a rede densa (NEWK, = malha 3× do VASP).

```bash
python3 $S/cry_input.py --geom runs/<f>_atomopt/fort.34 ... --func <F> --mode sp --k A B C --name <f>_sp
sbatch $S/job_crystal.sh runs/<f>_sp                                         # -> fort.9
~/micromamba/envs/render_env/bin/python $S/cry_kpath.py runs/<f>_sp/crystal.out   # -> KPATH_CRYSTAL
python3 $S/cry_props.py --scf-out runs/<f>_sp/crystal.out --what both --kpath-file runs/<f>_sp/KPATH_CRYSTAL
sbatch -t 04:00:00 $S/job_crystal.sh --props runs/<f>_sp
python3 $S/cry_parse.py bands runs/<f>_sp && python3 $S/cry_parse.py dos runs/<f>_sp
```

**Caminho = o mesmo do VASP.** O `gen_kpath.py` do repo VASP usa `pymatgen HighSymmKpath` (convenção **Setyawan–Curtarolo 2010**) com 40 pontos por segmento, e grava `POSCAR_bands` padronizado (exigindo novo SCF se a célula mudar). O `cry_kpath.py` usa a mesma chamada, mas em vez de mudar a estrutura converte os pontos para a base recíproca primitiva **do próprio CRYSTAL**: acha a matriz unimodular S que leva a célula padrão do pymatgen na do CRYSTAL, aceita só se ela também leva os **átomos** (simetria do cristal, não só da rede) e usa f_cry = f_std·S⁻ᵀ. Pontos irracionais (monoclínico: η, ν dependem de β) viram frações com ISS comum (Ag2SeO3: ISS 1800, erro 5×10⁻⁵ — aceito pelo CRYSTAL, testado). `NSUB` = 40 × nº de segmentos (o CRYSTAL distribui com passo constante, então não é exatamente 40 por segmento). O aviso do pymatgen "input structure does not match the expected standard primitive" é esperado e inofensivo aqui (a conversão cuida disso). Saídas: `KPATH_CRYSTAL` (ISS, DIV, segmentos com rótulos), `bands_ticks.csv` para o gráfico.

Exemplo verificado (Ag2SeO3 B3LYP k333, `fort.9` do job 876, 2026-11-17): caminho Γ–Y–H–C–E–M1–A–X–H1|M–D–Z|Y–D, 442 k, 20 s com 4 threads; VBM no segmento M1–A, CBM em Γ, gap indireto 3,845 eV no caminho contra 3,9135 eV na rede 3×3×3 do SCF — **o VBM verdadeiro fica fora da rede SCF** (a banda de valência sobe 0,07 eV acima do E_F da malha). Por isso relatar sempre o gap do caminho e o da rede.

`PROPS` gerado (exemplo MgO, verificado):
```
BAND
band structure
10 8 400 1 29 1 0         # NLINE ISS NSUB INZB IFNB IPLO(1=fort.25+BAND.DAT) LPR66
0 0 0 -4 0 -4             # segmentos em unidades de 1/ISS dos vetores recíprocos primitivos
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
- Alternativas ao `--kpath-file`: `--path "G X;X W"` (só rótulos das Tabelas 14.1/14.2; FCC aceita X, L, W e **não** K) ou `--path-frac`.
- Saídas: `fort.25` (blocos `-%-` BAND/DOSS com E_F), `BAND.DAT`, `DOSS.DAT` (E−E_F em Ha; projeções e total por último). `cry_parse.py` converte para eV (`bands.csv`: E−E_F; `DOS_raw_data.csv`: estados/eV/célula) e diz onde estão VBM/CBM (rótulo/segmento).
- Gap da rede SCF: `DIRECT/INDIRECT ENERGY BAND GAP` é impresso a cada ciclo — vale a **última** ocorrência.
- **GGA e híbrido:** rito completo com cada funcional (geometria própria; decisão do usuário 2026-11-17). Para comparar com VASP-HSE06 usar HSE06 aqui (ω = 0,11 bohr⁻¹, 25 %). Autovalores HF puros não são energias de excitação (p.309-310).

## 6. Spin, magnetismo, convergência difícil

- **Spin:** `--spin` (SPIN no bloco DFT) + `--spinlock "NALPHA-NBETA NCICLOS"` para fixar o momento no início; momentos por átomo com `ATOMSPIN` (no bloco 3, via `--extra3`); edição da matriz de spin `SPINEDIT` (p.128). Comparar ordens magnéticas como no VASP. NEWK IFE=1 obrigatório depois.
- **SCF lento/oscilante:** subir `FMIXING` (30→50–70), `LEVSHIFT "5 1"` (0,5 Ha, travado) para isolantes, `BROYDEN` (p.100), `ANDERSON` (p.98); `SMEAR` só para metais (implica gradientes numéricos na otimização). Depois de convergir com LEVSHIFT, os autovalores ficam deslocados → NEWK IFE=1 nas propriedades.
- **Chute de densidade:** `--guessp` lê `fort.20` (o job copia o `fort.9` do run dir) — útil para trocar de funcional na mesma geometria (PBE → HSE06).
- **Dispersão:** DFT-D3 / gCP / métodos 3c no cap. 5 (índice B "DFT-D3"); decidir com o usuário antes de usar.

## 7. Custos de referência (para estimar antes de submeter)
Ver `gotchas.md` §2. Regra prática: custo ∝ (nº de k na IBZ) × (nº de AO)³ na diagonalização + séries de troca (híbrido) que crescem com TOLINTEG; RSH ~2–3× um híbrido global; usar a simetria reduz k na IBZ e integrais.
