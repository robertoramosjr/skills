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
- `paper/Figures/DOS.eps` (PDOS a/b sem e com vacâncias) e `magnetic_moment_comparison.eps` (momentos a/b): já existem; referência = as próprias.
- **a (definida 2026-11-05):** pontos ligados por linha; x = distância Nd–V, y = energia de formação e ΔE (`Ef_calc/formation_energy_Ag_and_vacancies.csv` + distâncias medidas das CONTCAR). **Eixo y duplo** (E_f à esquerda, ΔE à direita), decidido 2026-11-05.
- **b (definida 2026-11-05):** pontos ligados por linha; x = distância ao Nd, y = momento magnético (`decay_{Ag,Cr,O}_vs_Nd_raw_data.csv`). Layout escolhido: 2 painéis em coluna simples (sem vacância; Ag_T_N), Ag/Cr/O sobrepostos, eixo y compartilhado; os 6 casos restantes no suplemento no mesmo formato.
- **d (modelo escolhido 2026-11-05):** E_f × Δμ_O (1D), retas do Nd_Ag e dos complexos Nd+2V_Ag em Ag-rico e Ag-pobre, faixa estável sombreada. μ_Nd vem do equilíbrio com Nd2O3 (μ_Nd = ½[E(Nd2O3) − 3μ_O]); limite Ag-pobre exige referência de óxido de Cr (ainda por definir) e depende do job 1910439.
- Pendente, **o usuário fornece a referência**: c = isosuperfície de densidade de spin.
