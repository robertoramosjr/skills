---
name: vasp_plot
description: Figuras de estudos VASP (DOS/PDOS spin-polarizado, momento magnético por átomo e decaimento com a distância ao dopante, energia de formação/defeitos, densidade de spin, estrutura 3D) a partir de CSV/OUTCAR/DOSCAR já extraídos, em qualidade de revista (EPS vetorial + PNG), no molde da turbo_plot. Use SEMPRE que o usuário pedir gráfico, plot ou figura de um cálculo VASP (Ag2CrO4:Nd, NaCoO2, BaZrS3, ...) — mesmo sem dizer "vasp_plot". Não extrai dados (isso é vasp-pipeline).
---

# vasp_plot — figuras do pipeline VASP

Estágio de figura: transforma dados já extraídos em figura. Não roda cálculo. Extração: skill `vasp-pipeline`.

## Regra dura: figura nova exige referência do usuário
**Antes de criar qualquer tipo de figura que ainda não exista, perguntar ao usuário por uma figura de referência** (de artigo ou dele) e só então escrever o script. Figuras já existentes em `paper/Figures/` só são regeradas/ajustadas a pedido. Nunca inventar o layout.
- Ao pedir a referência, dizer qual dado alimenta a figura (arquivo) e as 1–2 opções de layout que se imagina.
- Registrar o tipo e a referência recebida na seção "Figuras conhecidas" abaixo.

## Regras de figura (as mesmas da turbo_plot e de `research-paper-writing/references/user-style-comp-chem.md` §0)
- Texto dentro da imagem imprime em **10 pt** após a compilação: renderizar na largura impressa (`\columnwidth` revtex ≈ 86 mm, `figure*` ≈ 178 mm); fator = largura impressa / largura da fonte. Conferir ao incluir.
- Saída: `.eps` (vetorial, arquivo de submissão) + `.png` 300 dpi; uma figura por resultado, salvo pedido de painéis.
- Valores lidos dos CSV, nunca "de olho". Eixo de energia relativo a E_F; spin up positivo, spin down negativo.
- matplotlib (`numpy`, `matplotlib`); Veusz só se o usuário pedir (há `.vsz` nas pastas do Ag2CrO4).

## DOS/PDOS: regra (usuário, 2026-11-07; mesma da `turbo_plot` e da `academic-figure-skill`)
- **Normalizada por átomo:** TDOS ÷ nº de átomos da célula (área cinza clara sólida `#E3E3E3`, borda `#7A7A7A`, sem `alpha`); PDOS de cada elemento ÷ nº de átomos desse elemento (linhas). Unidade `DOS (states/eV/atom)`. Assim, células de 112 e 222 átomos e o dopante único ficam na mesma escala; dizer as duas normalizações na legenda e nos Métodos.
- **Mesma escala vertical em todos os painéis** (`sharey`), nunca "note the different scales".
- **Spin majoritário positivo:** em célula com M < 0 no VASP (ex. Ag_TeO_N1 e Ag_O_F, M = −3 µB) trocar os canais; `:auto` faz pela integral em E_F. Dizer na legenda.
- **Alargamento gaussiano σ = 0,1 eV só para exibição** (o DOSCAR com ISMEAR=0/SIGMA=0,01 sai em espinhos); é o mesmo do `dos_analysis.py`, que gerou os CSV antigos. Energia = E − E_F do cabeçalho do DOSCAR (o `dos_analysis.py` desloca para o VBM, ~0,1 eV de diferença).
- **Conferir o TDOS contra o NELECT** (DOSCAR com total ÷800: `vasp-pipeline/references/gotchas.md`); o script reescala e avisa.
- Estilo `turbo_plot`: moldura fechada, ticks para fora, serif (STIX). **Cores das linhas: paleta Origin (usuário, 2026-11-09)**: Ag `#000000`, Cr `#FF0000`, O `#0000FF`, Nd `#FF00FF` (1 preto, 2 vermelho, 3 azul, 4 magenta; `--palette okabe` volta ao Okabe-Ito antigo `#D55E00/#0072B2/#009E73/#CC79A7`), E_F tracejado, rótulo de estrutura com fundo branco sólido, legenda dentro do quadro em canto vazio (ou uma linha acima da figura quando há muitos painéis), rótulos `a)` `b)` em negrito.
- **Comparar estruturas:** no texto principal, só as que a discussão usa (dopante isolado × complexo mais estável); as demais configurações vão para o suplemento num painel por estrutura, ordenadas por ΔE, mesmo formato e escala. Sobrepor 7 curvas num painel não se lê. Curva do pristino como referência só com um DOS próprio (ISPIN, NEDOS=6001, mesma malha): o DOSCAR do Etot do pristino (NEDOS=301 padrão, ISPIN=1) é grosso demais.
- Script: `scripts/plot_dos_per_atom.py --panel DIR:RÓTULO[:auto|:flip] [...] --out PREFIXO --csv` (lê DOSCAR + CONTCAR, LORBIT=10/11; `--legend-loc top --label-pos ll` para a pilha do suplemento; `--csv` grava as curvas normalizadas ao lado da figura).

## Ferramentas existentes (repo `~/work_vasp/scripts/`)
`plot_dos.py`, `plot_bands.py`, `plot_bands_dos.py`, `plot_chg.py`, `magnetic_decay.py` (decaimento do momento vs distância ao Nd), `extract_magnetization.py`, `separate_spin.py`, `visualizar_poscar.py`, `plot_thermo.py`, `plot_stress.py`. Conferir o cabeçalho de cada um antes de usar; não duplicar.

## Dados típicos do Ag2CrO4:Nd (`paw_pbe_1.125xENMAX_Etot/DEFECT_MODELS/`)
| Dado | Arquivo |
|---|---|
| DOS por elemento e spin | `<pasta>/DOS_raw_data.csv` (Energy_eV, Total/Ag/Cr/O/Nd × Up/Down) |
| Momento por espécie | `<pasta>/magnetization_data.csv` |
| Momento vs distância ao Nd | `<pasta>/decay_{Ag,Cr,O}_vs_Nd_raw_data.csv` |
| Densidade de spin | `<pasta>/CHGCAR_SPIN` |
| Energias de formação | `Ef_calc/*.csv`, `formation_energy*.csv` |

## Figuras conhecidas
- **DOS (refeita 2026-11-07):** `paper/Figures/dos_per_atom.eps` (Fig. 4: a) Nd_Ag 112 at. em `paw_pbe_1.125xENMAX_DOS/DEFECT_MODELS/Ag_by_Nd_1`, b) Ag_TeO_N1 = `Ag_T_N_OK` com spins trocados) e `dos_complexes_SI.eps` (Fig. S1: os 7 complexos por ΔE); CSV `*_a.csv`… ao lado. Substituiu o raster GIMP `DOS.eps` (painel b era Ag_TeO_NeF), mantido só como histórico.
- `magnetic_moment_comparison.eps` (densidade de spin a/b): já existe; referência = a própria.
- **a (definida 2026-11-05):** pontos ligados por linha; x = distância Nd–V, y = energia de formação e ΔE (`Ef_calc/formation_energy_Ag_and_vacancies.csv` + distâncias medidas das CONTCAR). **Eixo y duplo** (E_f à esquerda, ΔE à direita), decidido 2026-11-05.
- **b (definida 2026-11-05):** pontos ligados por linha; x = distância ao Nd, y = momento magnético (`decay_{Ag,Cr,O}_vs_Nd_raw_data.csv`). Layout escolhido: 2 painéis em coluna simples (sem vacância; Ag_T_N), Ag/Cr/O sobrepostos, eixo y compartilhado; os 6 casos restantes no suplemento no mesmo formato.
- **d (modelo escolhido 2026-11-05):** E_f × Δμ_O (1D), retas do Nd_Ag e dos complexos Nd+2V_Ag em Ag-rico e Ag-pobre, faixa estável sombreada. μ_Nd vem do equilíbrio com Nd2O3 (μ_Nd = ½[E(Nd2O3) − 3μ_O]); limite Ag-pobre exige referência de óxido de Cr (ainda por definir) e depende do job 1911421.
- Pendente, **o usuário fornece a referência**: c = isosuperfície de densidade de spin.
- **Configurações Nd_Ag + 2V_Ag (Fig. 1 do paper 2, criada 2026-11-09, 1ª tentativa sem referência por autorização do usuário; ele manda um modelo se não servir):** `scripts/plot_vacancy_configs.py` (render_env + POV-Ray; 7 painéis + legenda, 178 mm, PNG 600 dpi + EPS raster). Nd no poliedro de O, Ag pálido, **átomo fantasma** (esfera branca translúcida) no centro do poliedro de O do sítio vacante (tetraedro = Ag2/T, octaedro = Ag1/O); CrO4 omitido. Nomenclatura `2V_{Ag,XYn}` (T/O + posto por distância): mapa em `CONFIGS` do script e em `paper/plano_narrativo_paper2.md`. `gs` não existe no login node: o EPS sai sem validação.
