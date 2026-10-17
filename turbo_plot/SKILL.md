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
| Figura de espectros de uma pasta de cálculo (UV-vis, IR, TDOS) | `scripts/plot_spectra.py` (matplotlib, EPS + PNG, padrão de revista) |
| Figura de paper com layout fino, rótulos, múltiplos painéis | Veusz (`veusz_env`), scripts `veusz/plot_*.py` do repo |
| Espectro/DOS de outro estudo que já tem `plot_*_matplotlib.py` | o script existente, conferindo as regras da seção 3 |
| Figura de revista de outro tipo (barras, scatter, heatmap) | `academic-figure-skill` (fluxo completo, `references/`) |

Rode o `plot_spectra.py` a partir da pasta do cálculo ou com `--dir`:

```bash
python ~/.claude/skills/turbo_plot/scripts/plot_spectra.py --dir <pasta_do_calculo> --output <pasta>/spectra_<molecula> --width double
```

`--output` é o nome sem extensão: o script grava `<nome>.eps` (master vetorial, o arquivo de submissão) e `<nome>.png` (preview 300 dpi). `--width single` usa a coluna de 89 mm; `double` (padrão), 183 mm. Ele pula com aviso os arquivos que faltarem. Dependências: `numpy` e `matplotlib`.

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
- **Rótulos de painel no formato `a)`, `b)`, `c)`**, em negrito, fora do canto superior esquerdo da moldura.
- **Legenda dentro da moldura**, em região vazia. Se não houver espaço, aumente o limite do eixo (~30 % de folga no topo) em vez de encostar a legenda nos dados. O script já faz isso.
- **Notas de texto** (ex.: "ρ = …", "sTDA ~1,2 eV baixo") ficam acima da moldura, alinhadas à direita, nunca sobre os dados.
- **Sem transparência (`alpha`) no master.** O script usa cores opacas; a área do DOS é preenchida com cor clara sólida.
- **Paleta:** Okabe-Ito (azul para a curva, laranja para os sticks, verde para o DOS). Cores sólidas e seguras para daltonismo.
- **Picos de IR:** a regra do Roberto (2026-10-16) pede o rótulo do modo normal nos **5 picos mais intensos** (só o caráter, ex.: `γ(C–H)`, sem o número). Isso requer o arquivo `vib_normal_modes`, que o `aoforce` grava. A pasta de espectros atual **não tem** esse arquivo, então essa rotulagem ainda não está no `plot_spectra.py`. Para incluir, use `~/skills/academic-figure-skill/scripts/ir_mode_assign.py` (função `peak_labels`) e a receita de `~/skills/academic-figure-skill/references/ir-spectra.md`. Diga na legenda que é o caráter dominante, não PED completa.
- **Veusz (alternativa de layout):** `LC_ALL=C` (ponto decimal); ambiente `veusz_env`. Locale pt_BR quebra a leitura de números.
- **Renderização 3D/2D de estrutura e isosuperfícies** usam `vasp_env` (rdkit/ase/povray). Estrutura é raster de verdade: PNG 600 dpi dentro do EPS, sem moldura. Regras em `~/skills/academic-figure-skill/references/structure-renders.md`.

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

- `scripts/plot_spectra.py` — figura de três painéis de espectros de uma pasta (`--help` para as opções).
- `~/skills/academic-figure-skill/references/` — detalhe de `typography.md`, `export-specs.md`, `journal-specs.md`, `color-palettes.md`, `ir-spectra.md`, `structure-renders.md`.
- Mapa de scripts de figura do repo: `~/.claude/skills/turbomole-pipeline/references/scripts-map.md`, seção "Espectros/figuras".
