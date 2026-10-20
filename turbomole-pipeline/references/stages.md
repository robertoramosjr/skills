# Estágios do pipeline — comandos e verificações

Fonte de verdade longa: `MANUAL.md` e `pipeline_extracao_dft.md` na raiz do repo (eles ainda dizem "PBS"; o cluster é **SLURM** — adapte `qsub/qstat` → `sbatch/squeue`). Aqui está o resumo operacional.

Conteúdo: [1 — Estágio 1](#1-estágio-1--cálculos-base) · [2 — DOS/PDOS](#2-dospdos) · [3 — Opcionais](#3-opcionais) · [4 — Extração](#4-extração-estágio-2) · [5 — Figuras](#5-figuras-estágio-3)

Trabalhe **sempre numa cópia** (`cp -r producao producao_<tag>`) para: DOS extra, broken-symmetry, orbitais/NTO, Raman, `freeh`. Esses estágios regravam `control` ou deixam `$actual step`/`$pointval` e sujam a produção.

## 1. Estágio 1 — cálculos base

```bash
jobex -c 800 > jobex.out            # exigir GEO_OPT_CONVERGED; senão NÃO seguir
ridft > ridft.out                   # SCF base (HSE06 + D3(BJ) + senex)
cp control control.pre_proper       # ANTES do -proper (ver armadilha pointval)
ridft -proper > proper.out          # gera td.cub (precisa $pointval fmt=cub no control)
BADER_BIN=$(command -v bader || echo ~/local_bin/bader)
$BADER_BIN td.cub > bader_run.out ; tail -5 ACF.dat   # elétrons integrados vs. esperado
mv control.pre_proper control       # restaura (sem $pointval explícito)
ridft > ridft_tight.out             # reconverge densidade antes do TD-DFT
escf > escf.out                     # TD-DFT (rpas; $soes a <N>)
aoforce > aoforce.out               # IR; grep -i imaginary
dscf -proper > pop.out              # Mulliken + SEN (precisa $pop)
```

**Checagens antes do Estágio 2**
- `grep -A 4 "HOMO-LUMO Separation" proper.out`
- `tail -5 ACF.dat` ≈ Z total (cubo `fmt=cub` grosso **perde caroço** de átomos pesados: Ni-PBE integrou 331,88 vs 334,00 e⁻ → cargas de metais não confiáveis; decidir grid mais fino ou Mulliken/Löwdin/NBO)
- `awk '$1 ~ /^[0-9]+$/ && $1 > 6 {print $3}' vibspectrum | sort -n | head -5` → sem negativo
- tempo de cada estágio ≫ 0 s (≈0 s com exit 0 = falha silenciosa por `$actual step`)

**TD-DFT:** 60 estados singletos no Paper 1; `$scfinstab rpas` (sem TDA) + `$soes a 60`; TDA = `ciss`; UHF = `urpa`. Alargamento Gaussiano: σ = 0,05 eV (FWHM ≈ 0,12 eV) nos espectros do Paper 1; 0,4 eV na JDOS. `Δf` entre funcionais é o proxy de CT.

**Retomada:** `jobex` não trava com `GEO_OPT_RUNNING` pré-existente — reexecutar. `aoforce` morto por walltime deixa `$actual step force` → `actual -r`; retomada só do rabo (aoforce + dscf -proper): `scripts/scripts/job_resume_force_pop.sh`.

## 2. DOS/PDOS

`<N_MOs>` = nº de funções de base (`grep -n "nbf(AO)" control` ou `grep -A 3 "SCF-basis functions" ridft.out`). Faixas de átomo pela ordem do `$coord` (a 1ª linha `natoms=` não conta como átomo). **Nunca** cole placeholder literal.

```bash
set_pop() {   # o dscf CONSOME $pop: sed simples falha em silêncio na 2ª chamada
  if grep -q '^\$pop' control; then sed -i "s/^\$pop.*/\$pop $1/" control
  else sed -i "/^\$end/i \$pop $1" control; fi
}
set_pop "mo 1-<N_MOs> dos";                 dscf -proper > dos_total.out;   ls -la dos && mv dos dos_total
set_pop "mo 1-<N_MOs> dos atoms <range_C>"; dscf -proper > dos_carbon.out;  ls -la dos && mv dos dos_carbon
# idem p/ hidrogênio e 4º elemento (O/N)
set_pop "mulliken loewdin nbo paboon"       # restaura $pop p/ a população
```
Confirme que `dos` existe **antes** do `mv` (senão move um `dos` antigo).

PDOS Mulliken por elemento pode ter canais **negativos** (artefato). Alternativas sem o artefato: Becke (por elemento, espaço real) e SCPA (elemento × s/p), via `tm2molden` → `Molden2AIM` → `Multiwfn_noGUI`. Binários em `~/local_bin/` (nunca dentro da pasta de cálculo). `tm2molden` pede **2** linhas em branco. Sanidade: soma das PDOS Becke = TDOS (<1e-6). **SCPA elemento × l (validado no azobenzeno, 2026-10-16):** script em stdin no Multiwfn sobre `molden_new.molden`: `10`,`7`,`2`(SCPA),`-1`; por fragmento `i`,`cond`,`<Elem>`,`<Enter>`,`<S|P|D|F>`,`q`; depois `e`,`0`,`-3`,`2`,`<emin emax passo a.u.>`,`3`,`0.005`,`0`,`3`. def2-TZVP em C/N/H = 10 fragmentos (C/N × s,p,d,f + H × s,p). Resultado: todos ≥ 0, soma/TDOS = 1±3e-5. Receita completa: `MANUAL.md` §7 do repo `turbomole`. Se o DOS cru tiver "pente", faltou smearing: checar se já existe `*_smeared.dat` antes de re-derivar σ (artepilina C: +0,4 eV).

## 3. Opcionais

- **Estabilidade + broken-symmetry (1c) — OBRIGATÓRIO (regra dura 7; metal/camada aberta/gap pequeno):** cópia separada do `GEO_OPT_CONVERGED` (`cp -r … stab_<tag>`), mesmo funcional/base/grid/`$disp3`/`$scfconv`.
  1. **Restrito/UHF de referência:** `ridft` → E_ref e, se UHF, `⟨S²⟩` (ideal S(S+1); contaminação > 0,05 é sinal).
  2. **Teste de instabilidade:** `escf` com `$scfinstab` (singleto/tripleto no RKS; `urpa` no UHF) **sem** `$soes`; autovalor negativo ⇒ instável. Conferir no texto do `escf.out` o que o build imprime na 1ª vez (não presumir formato).
  3. **BS (singleto camada aberta):** tripleto UHF (`t` no `define`) → reabrir `define` aproveitando `mos` → igualar `$alpha shells`/`$beta shells` (Ms=0), SCF até convergir; `flip` do `define` não é confiável e `$soes`/`flip` escritos direto falham em silêncio. Para dupleto/spin alto, testar também outra multiplicidade/ordem de ocupação do metal (d-orbital).
  4. **Decisão:** ΔE = E_BS − E_ref. |ΔE| < 1e-5 Eh e sem autovalor negativo ⇒ estável ⇒ `echo "E_ref=… E_BS=… dE=… S2=…" > .stages/STABILITY_OK`. ΔE < −1e-5 Eh ou instável ⇒ **a solução de partida está errada**: reotimizar (`jobex`) e refazer freq/pop/espectros a partir do `mos` BS; só então gravar o gate.
  5. Registrar no cofre a nota-estado com E_ref/E_BS/ΔE/⟨S²⟩ e as cargas só depois do gate.
- **GW / GW-BSE (1d):** `setup_gw_bse_template.py --xyz m.xyz --charge 0 --functional hse06 --nstates 10 --output-dir gwbse`. Duas rodadas `escf` com `control` distintos: `gwbse/gw` (ridft+escf → `qpenergies.dat`, fullspec) e `gwbse/bse` (copiar `qpenergies.dat`, ridft+escf → `escf_bse.out`). Sanidade: as energias de orbital nas "Dominant contributions" do BSE têm de bater com a coluna G0W0. Só validado em H2O; PBE0/RI-GW e UHF não testados.
- **HOMO/LUMO e NTO (1e):** `$pointval mo <HOMO>-<LUMO> fmt=cub` + `dscf -proper`. NTO: `proper` interativo → `mos` → `dftnto` → estado `1` → definição **`1`** (a `2` dá SIGSEGV em `cc_ntos.f:129`, TM 7.8.1) → `$pointval nto <idx> fmt=cub` + `dscf -proper`. Confirmar que a `Frequency` impressa bate com a energia do estado no `escf.out`. Render headless: `render_cube_isosurface.py --cube X.cub --out X.png --isovalue 0.03` (documente o isovalor). Sem `dftnto` → reportar e parar.
- **Raman (1f):** 3 passos — `aoforce` (já feito) → `egrad` com `$scfinstab polly` → `intense` (projeta nos modos; **não rodar sem os dados do polly**, roda "em vão"). Custo ≈ `aoforce`; vai por `sbatch`. **Validado 2026-10-17 (Ni(CO)4, 24 s CPU):** copiar o dir do `aoforce`, remover `$scfinstab rpas`/`$soes`, `egrad` e `intense` geram `$raman spectrum` no `control`; GPU: `job_raman_egrad_gpu.sh` (Ni HSE06 em `gpu_test/ni_raman_egrad`). Cópia separada; `$disp3/$senex/gridsize/$scfconv` idênticos à produção. Se `egrad`/`intense` reclamar de `$senex`/`$rik`, reportar o erro exato em vez de trocar o esquema de troca.
- **Diagnóstico de esquema de população (1b-alt):** quando a pDOS s/p/d por Mulliken tem dip negativo, comparar Mulliken × Löwdin × NBO numa cópia.

## 4. Extração (Estágio 2)

Parsers só precisam de `numpy` (rodam em nó sem Qt). Lista e flags: `references/scripts-map.md`. Padrão:

```bash
python ../scripts/parse_bader.py --acf ACF.dat --coord coord --output bader_dataset.dat
python ../scripts/parse_homo_lumo.py --proper proper.out --output homo_lumo_dataset.dat
python ../scripts/parse_excitations.py --escf escf.out --output-sticks excitation_sticks.dat \
       --output-jdos jdos_dataset.dat --broadening 0.4 --npoints 2000
python ../scripts/parse_ir.py --vibspectrum vibspectrum --output ir_dataset.dat   # descarta 6 modos
python ../scripts/parse_mulliken.py --pop pop.out --output mulliken_dataset.dat
python ../scripts/parse_bond_order.py --pop pop.out --output bond_order_dataset.dat
```
Armadilhas: `parse_bader.ATOMIC_NUMBER` só ia até Ca (corrigido para Sc–Zn; confira Z de elementos pesados). Sem `$pop mulliken loewdin nbo paboon` no `control`, o `pop.out` sai **sem** Mulliken/SEN ("No Mulliken charge rows"). Bonds entre confôrmeros: casar por isomorfismo do grafo, não por índice. Parsers não validam a física — só o formato.

## 5. Figuras (Estágio 3)

Movido para a skill `turbo_plot` (`~/.claude/skills/turbo_plot/SKILL.md`): ferramentas (Veusz × matplotlib), entradas e unidades, regras de locale e ambiente, e verificação da figura.
