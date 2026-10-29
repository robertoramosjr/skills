---
name: turbo_plot
description: Plota as figuras de um estudo TURBOMOLE (UV-vis, IR, DOS/TDOS/PDOS, RDF, especiação vs pH, isosuperfícies de orbital/cubo, estrutura 3D) a partir dos .dat/.csv já extraídos, em qualidade de publicação (EPS vetorial + PNG de conferência, formato de revista). Use SEMPRE que o usuário pedir gráfico, plot, figura, espectro, "plota isso", "faz o gráfico dos espectros", "figura para o paper", "figura para submissão", "põe no Veusz", "matplotlib", ou tiver datasets de Turbomole na pasta e quiser visualizar — mesmo sem dizer "turbo_plot". Também use quando uma figura sair em branco, com eixo errado ou fora do padrão da revista. Não use para extrair dados dos outputs (isso é a skill turbomole-pipeline).
---

# turbo_plot — figuras do pipeline TURBOMOLE

Estágio 3 do pipeline: transforma datasets já extraídos em figura. Não roda cálculo nem parser. Se a pasta ainda tem só `vibspectrum`, `exspectrum`, `control`, `dos_multiwfn.log`, primeiro gere os `.dat` (ver `turbomole-pipeline`, `references/scripts-map.md`, Estágio 2).

Esta skill absorveu as regras de figura de `academic-figure-skill` (`~/skills/academic-figure-skill`). Aquela skill continua intacta e é a fonte dos detalhes; aqui ficam só as regras que o plot de espectros usa.

## 1. Escolha a ferramenta

| Situação | Use |
|---|---|
| Figuras de espectros de uma pasta de cálculo (UV-vis, IR, TDOS), uma figura por resultado | `scripts/plot_spectra.py` (matplotlib, EPS + PNG, padrão de revista) |
| Figura de paper com layout fino, rótulos, múltiplos painéis | Veusz (`veusz_env`), scripts `veusz/plot_*.py` do repo |
| Espectro/DOS de outro estudo que já tem `plot_*_matplotlib.py` | o script existente, conferindo as regras da seção 3 |
| Figura de revista de outro tipo (barras, scatter, heatmap) | `academic-figure-skill` (fluxo completo, `references/`) |

Rode o `plot_spectra.py` a partir da pasta do cálculo ou com `--dir`:

```bash
python ~/.claude/skills/turbo_plot/scripts/plot_spectra.py --dir <pasta_do_calculo> --output <pasta>/spectra_<molecula> --width double
```

**PDOS (elementos, Ni×momento angular):** `scripts/plot_pdos.py --curve DOS_curve.txt --labels Ni S N O C H --orginfo orginfo.txt --xlim -20 5 --output <prefixo>` (`--no-opdos` para Becke; `--no-tdos` para PDOS de um só átomo). O `DOS_curve.txt` vem do Multiwfn (menu 10; `MANUAL.md` §6–7 do repo turbomole).
- **Qual método (decidido 2026-10-17, Ni-singleto):** **elemento → Becke** (menu `10`→`7`→`4`; fragmentos por *átomos*, ex. `67`, `65-66`, `1-2`); roda em ~10 s com 1503 funções, soma = TDOS (1,000000) e é robusto para virtuais. **Elemento × momento angular → SCPA** (`7`→`2`, fragmentos por `cond`); o Multiwfn avisa que SCPA/Mulliken não são robustos para orbitais desocupados, então só use SCPA abaixo do LUMO ou diga a ressalva. Becke não resolve s/p/d.
- **Colunas do `DOS_curve.txt`:** energia(a.u.) | TDOS | **OPDOS(1,2) só em SCPA/Mulliken com ≥2 fragmentos** | fragmentos. Becke não tem coluna OPDOS (`--no-opdos`); errar isso desloca todas as curvas em uma coluna (sintoma: o elemento dominante aparece com o rótulo errado e a soma/TDOS cai a 0,66). Confira sempre soma/TDOS ≈ 1.
- **UHF (Cu, camada aberta, 2026-10-29):** `scripts/molden_uhf_for_multiwfn.py --molden <mol.molden> --nalpha <n> --nbeta <n>` (reagrupa α/β, mantém virtuais). No Multiwfn inserir `6`,`3` (*Both spins*) logo após o `10`; sem isso o PDOS sai só α. `orginfo.txt` do Multiwfn pode vir em **hartree** (HOMO ≈ −0,2): passar `--orginfo-au` ao `plot_pdos.py`, senão a linha HOMO/LUMO cai em −0,2 eV.
- **Molden para o Multiwfn:** `scripts/molden_for_multiwfn.sh [nocc] [molden]` na pasta de trabalho gera `molden_new.molden` esférico **com os virtuais**. O `molden2aim` descarta orbitais com `Occup=0` (PDOS some acima do HOMO) e sai com código ≠ 0 no prompt final; o script marca todos como 2,0, converte e restaura 0 acima do HOMO. O `molden` cru do `tm2molden` sem `[5D7F]` é lido como cartesiano (Tr(S·P) errado), não serve.

**Uma figura por resultado, nunca tudo junto num painel múltiplo** (pedido do usuário). `--output` é o prefixo: o script grava `<prefixo>_uvvis`, `<prefixo>_ir` e `<prefixo>_dos`, cada um em `.eps` (master vetorial, o arquivo de submissão) e `.png` (preview 300 dpi). `--only ir` gera só uma. `--width single` (padrão) usa a coluna de 89 mm; `double`, 183 mm. Ele pula com aviso o que faltar. Dependências: `numpy` e `matplotlib`.

A figura de IR rotula os 5 picos mais intensos com o caráter do modo normal quando a pasta tem `coord`, `vib_normal_modes` e `vibspectrum` (`--ir-labels 0` desliga). O `vib_normal_modes` vem do `aoforce` e nem sempre fica na pasta de espectros: procure na pasta de produção e em `metal_complexes/gpu_test/*/`, e confira que `coord` e `vibspectrum` são os mesmos (`diff`) antes de copiar.

## 2. Entradas esperadas

| Arquivo | Colunas usadas | Unidades |
|---|---|---|
| `uvvis_broadened.dat` | λ (nm), energia (eV), intensidade ampliada (3ª coluna) | nm / eV / a.u. |
| `uvvis_sticks.dat` | λ (nm), energia (eV), força do oscilador | nm / eV / a.u. |
| `ir_broadened.dat` | número de onda, intensidade | cm⁻¹ / km mol⁻¹ |
| `ir_sticks.dat` | número de onda, intensidade | cm⁻¹ / km mol⁻¹ |
| `dos_tdos.dat` | energia, TDOS | eV / arb. |

Os `.dat` são gerados pelo `tm_spectra.py` (IR/UV-vis) e pelo `tm_dos.py` (DOS). Antes de plotar, confira o cabeçalho com `head -2 <arquivo>` — a coluna certa muda se o gerador mudou. Os arquivos têm linha `#` no topo.

## 3. Padrão de publicação (regras herdadas de academic-figure-skill)

- **Master vetorial em EPS**, com fontes TrueType embutidas (`ps.fonttype 42`). PNG 300 dpi é só conferência. Antes de entregar, confira que o `.eps` não tem raster escondido (`alpha` e `rasterized=True` são as causas comuns): `grep -c "BeginImage\|colorimage" <arquivo>.eps` deve dar 0.
- **Tipografia serif:** Times New Roman, com fallback Liberation Serif / Nimbus Roman / STIX. Nesta máquina só STIX está instalado, e ele tem métrica de Times. Sem texto abaixo de 5 pt no tamanho final.
- **Largura de coluna fixa:** 89 mm (uma coluna) ou 183 mm (duas). Monte a figura já nessa largura; nunca reduza depois.
- **Moldura fechada** (quatro lados), sem grade. Ticks para fora.
- **Rótulos de painel `a)`, `b)`, `c)`** (negrito, fora do canto superior esquerdo) só quando houver mais de um painel numa figura. Espectros saem um por figura, então não levam rótulo.
- **Legenda dentro da moldura**, em região vazia. Se não houver espaço, aumente o limite do eixo (~30 % de folga no topo) em vez de encostar a legenda nos dados. O script já faz isso.
- **Notas de texto** (ex.: "ρ = …", "sTDA ~1,2 eV baixo") ficam acima da moldura, alinhadas à direita, nunca sobre os dados.
- **Sem transparência (`alpha`) no master.** O script usa cores opacas; a área do DOS é preenchida com cor clara sólida.
- **Paleta:** Okabe-Ito (azul para a curva, laranja para os sticks, verde para o DOS). Cores sólidas e seguras para daltonismo.
- **Picos de IR:** regra do Roberto (2026-10-16): rótulo do modo normal nos **5 picos mais intensos**, só o caráter (ex.: `γ(X–H)`), sem o número de onda. `scripts/ir_mode_labels.py` faz isso para complexos metálicos: decompõe a energia cinética de cada modo por papel do átomo (H–X, metal, átomo doador e seu parceiro, par N–N, esqueleto) e dá o caráter dominante. Rode `python ir_mode_labels.py --folder . --table` para ver as frações e conferir a sanidade (ν(X–H) em ~3000–3600, γ(C–H) em ~650–850, ν(C=N) em ~1600–1700). O `ir_mode_assign.py` da academic-figure-skill é só para corante azo e não conhece metais. Na legenda da figura, diga que é o caráter dominante (decomposição da energia cinética), não uma PED completa. Os picos rotulados ficam a pelo menos 100 cm⁻¹ um do outro para os textos verticais não colidirem.
- **Formato do `vib_normal_modes`:** campos de largura fixa (componente nas colunas 1–3, bloco de 5 modos nas colunas 4–5). A partir do bloco 10 os campos se encostam (`  110`), então um `split()` perde essas linhas. Com `split` este arquivo (67 átomos) lê só 45 dos 201 modos.
- **Veusz (alternativa de layout):** `LC_ALL=C` (ponto decimal); ambiente `veusz_env`. Locale pt_BR quebra a leitura de números.
- **Isosuperfícies de NTO/orbital (cubo):** ver seção 3D, `render_nto.py` (`render_env`).
- **Renderização 3D/2D de estrutura** usa `render_env`/`vasp_env` (rdkit/ase/povray). Estrutura é raster de verdade: PNG 600 dpi dentro do EPS, sem moldura. Regras em `~/skills/academic-figure-skill/references/structure-renders.md`.

## 3D. Isosuperfícies de NTO/orbital a partir de cubo (`render_nto.py`)

Referência visual: `artepillin_C_studies/nto/conf_1_LUMO_82a.eps` (molécula bola-e-bastão no estilo VESTA + lóbulos translúcidos amarelo = +, ciano = −; o EPS de referência é um raster embutido, feito com VESTA).

```bash
~/.conda/envs/render_env/bin/python ~/.claude/skills/turbo_plot/scripts/render_nto.py <S1/nto_vir_1.cub> --iso 0.03 --width-mm 178 --dpi 300 -o <prefixo>   # .pov + .png + .eps
```
- **Método:** lê o cubo (`$pointval nto 1-2 fmt=cub`, de `job_nto_cubes.sh`; unidades em bohr, convertidas para Å), gera a malha com `skimage.measure.marching_cubes` (±iso), orienta a molécula com `orient()` do `render_structures.py` da academic-figure-skill (mesma regra de vista, a transformação é aplicada à malha por ajuste afim nos átomos) e renderiza no POV-Ray (`mesh2`, `rgbt` com transmit 0,55, sem sombra nos lóbulos). EPS = PNG dentro (Flate), validado com `gs -sDEVICE=nullpage`. Raster de verdade, por isso a regra "sem raster" do EPS vetorial não vale aqui.
- **Ambiente `render_env`** (povray, ase, pillow, scipy) **+ `scikit-image`** (instalado com `pip install scikit-image`; não vem por padrão). O `paper2_funnel` e o `vasp_env` não são necessários.
- **Arquivos:** `nto_occ_1.cub` = buraco (par 1), `nto_vir_1.cub` = elétron (par 1); `_2` = segundo par NTO (no Paper 2 o par 1 pesa 83–99,97 % da transição, então as grades usam só o par 1). Um EPS por cubo.
- **Saídas por cubo:** `.pov` (cena editável), `.png`, `.eps` (PNG dentro) e **`.vesta`** para ajuste manual. O `.vesta` traz a estrutura no referencial do próprio cubo (sem reorientar), a célula = caixa da grade e `IMPORT_DENSITY` apontando o `.cub` por **caminho relativo** ao `.vesta` (mantenha o symlink `source/` ao lado). O `ISURF` NÃO é gravado (formato não verificado, VESTA não roda no cluster): no VESTA, Properties → Isosurfaces, "both signs", nível = isovalor usado, amarelo (+)/ciano (−), opacidade ~45 %. **Nunca abri um `.vesta` gerado aqui no VESTA**; se não abrir, reportar.
- **Orientação determinística:** `prepare()` arredonda as coordenadas a 1e-3 Å antes de `orient()` (o sinal da normal por SVD pode virar com ruído de 1e-6 e girar a molécula 180° entre o cubo do buraco e o do elétron).
- **Isovalor:** 0,02 enche a figura de lóbulos pequenos em H e O; **0,03 é o padrão**. Use o mesmo valor em todas as figuras comparadas e diga-o na legenda.
- `--step 2` (marching cubes mais grosso) e `--dpi 150` dão prévia em ~20 s; 300 dpi/step 1 para o master.

### Grades (`nto_grid.py`)
```bash
~/.conda/envs/render_env/bin/python ~/.claude/skills/turbo_plot/scripts/nto_grid.py --nto-root <nto> \
   --rows vac/N_job_0044:2:N vac/A_job_0093:23:A -o <saida> --width-mm 178     # dir:raiz:rótulo
```
Linhas = (estado, raiz); colunas = buraco | elétron (par 1). **Mesma escala em todas as células** (janela comum = maior extensão), moldura ausente, rótulos `a)`, `b)` em negrito (STIX, 10 pt no tamanho final), λ, f e peso do par 1 em cada linha (lidos de `escf.out`/`dftnto.out`), legenda de fases + isovalor embaixo. Saída `.png` + `.eps` (PNG dentro); células soltas em `<saida>_cells/`.
- Convenção do Paper 2 (`Figures/nto/render_grids.sh`): **principal** = uma grade em vácuo (N, A, B, D) e uma em água (N, A), cada estado na raiz de maior f; **suplementar** = uma grade por (ambiente, estado) com todas as raízes calculadas.
- Testado em `vac/A_job_0093/S1/nto_vir_1.cub` e nas grades do Paper 2 (2026-10-20).
- Pendente: recorte da margem entre linhas, etiquetas de orbital (HOMO/LUMO) e grade com mais de 2 colunas.

## 4. Outras regras

- **Figura em branco ou com eixo absurdo = dataset errado ou coluna divergente.** Confira `head -1` e as unidades antes de mexer no estilo.
- **Scripts específicos de artepilina C** (`plot_bond_order_artepillinC.py`, `plot_bond_order_structure_artepillinC.py`, `plot_molecule_vesta_style.py`) têm listas e rótulos hardcoded. Não reaproveite sem revisar.
- **Flags locais de `veusz/plot_dos.py` e `veusz/plot_rdf.py`** (`--element4-label`, `--homo-lumo`, `--columns`) foram derrubadas por um merge do upstream. Confira as flags com `--help` antes de aceitar a versão remota.
- Nomeie a figura com o estudo e o conteúdo (`spectra_<molecula>`), e diga no texto qual versão de TM e de funcional gerou os dados.

## 5. Verificação antes de entregar

1. Abra o PNG de conferência (ferramenta de leitura de imagem) e confira se a curva está no lugar, os eixos batem com as unidades da tabela e a legenda não cobre dado.
2. Confira se os picos esperados aparecem: por exemplo, UV-vis e IR com um pico forte perto do valor de `exspectrum`/`vibspectrum`.
3. Confira o `.eps` (comando da seção 3) e que as fontes estão embutidas.
4. Se algum painel saiu vazio, o aviso de arquivo ausente no stderr é a primeira pista.

## 6. Referências

- `scripts/plot_spectra.py` — figuras de espectros de uma pasta, uma por resultado (`--help` para as opções).
- `scripts/render_nto.py` — isosuperfícies de NTO/orbital de cubos `.cub` (VESTA-style, EPS+PNG+.vesta).
- `scripts/nto_grid.py` — grades de renders de NTO (buraco | elétron) em escala comum.
- `scripts/ir_mode_labels.py` — caráter dominante dos modos normais e rótulos dos picos de IR.
- `~/skills/academic-figure-skill/references/` — detalhe de `typography.md`, `export-specs.md`, `journal-specs.md`, `color-palettes.md`, `ir-spectra.md`, `structure-renders.md`.
- Mapa de scripts de figura do repo: `~/.claude/skills/turbomole-pipeline/references/scripts-map.md`, seção "Espectros/figuras".
