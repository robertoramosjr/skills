# Espectros IR/FTIR calculados: picos rotulados com o modo (regra do Roberto, 2026-10-16)

**Regra:** todo plot de IR/FTIR leva, sobre os **5 picos mais intensos de cada espectro**, um texto vertical com
**só o caráter do modo, sem o número de onda** (ex.: `γ(C–H)`, `ν(N=N) + ring ip`; o número já está no eixo x. Pedido do Roberto, 2026-10-16). `peak_labels(..., show_freq=True)` devolve `718 · γ(C–H)` se algum dia for preciso. Isso dá robustez à figura: o leitor vê a
que movimento cada banda corresponde. **Só 5**: rotular tudo polui (pedido explícito do Roberto).

- O rótulo vem dos **modos normais calculados**, não de memória nem de tabela de literatura. Script:
  `scripts/ir_mode_assign.py` (Turbomole: `coord`, `vib_normal_modes`, `ir_dataset.dat`).
  `peak_labels(folder, top_n=5, merge=50, show_freq=False)` devolve `[(cm-1, intensidade, texto)]`.
- Método: decomposição da energia cinética de cada modo por átomo em ν(C–H), δ(C–H), γ(C–H), ν(N=N), ν(C–N),
  torção CNNC, anel no plano (`ring ip`) e fora do plano (`ring oop`); rótulo = categoria dominante + a segunda se
  tiver ≥ 22 %. É **caráter dominante, não PED completa**: dizer isso na figura/legenda
  ("Labels: five most intense peaks; dominant character of the calculated normal mode (kinetic-energy decomposition); ip/oop = in-plane/out-of-plane").
- Idioma do rótulo = idioma da figura (artigo em inglês: `ring ip/oop`, `CNNC torsion`).
- Outros códigos (VASP, CP2K): o script lê Turbomole; para outro código, converta os autovetores para `vib_normal_modes`
  equivalentes (deslocamentos cartesianos por modo, ordem crescente de frequência) ou adapte `read_modes`.
- Conferir a sanidade das atribuições: ν(C–H) em ~3000–3250, γ(C–H) e flexão do anel fora do plano em 650–850,
  δ(C–H) em 1000–1300, ν(N=N) em 1400–1700. Atribuição absurda = bug de ordenação dos modos ou de unidade (`coord` está em bohr).

## Trecho de plot (matplotlib) — texto vertical e eixo y esticado só o necessário

```python
import sys, os; sys.path.insert(0, os.path.expanduser("~/skills/academic-figure-skill/scripts")); import ir_mode_assign as ima

def annotate_ir(fig, a, x, cur, labels):
    ymax = cur.max(); a.set_ylim(0, ymax * 1.35); texts = []
    for w, I, txt in labels:
        y0 = cur[np.argmin(abs(x - w))] + 0.02 * ymax
        texts.append((y0, a.text(w, y0, txt, rotation=90, ha="center", va="bottom", fontsize=6.5, color="0.15")))
    fig.canvas.draw(); hax = a.get_window_extent().height
    need = max(y0 / (0.95 - t.get_window_extent().height / hax) for y0, t in texts)
    a.set_ylim(0, max(ymax * 1.35, need))

# depois de fig.tight_layout():
for a, i in zip(axs, iso): annotate_ir(fig, a, x, curves[i], ima.peak_labels(f"{ROOT}/azo_{i}_hse06_m4_d3", top_n=5))
```
Detalhes que evitam colisão: nome do painel (`cis`/`trans`) fora da região dos picos altos (x ≈ 0.30 do eixo), nota de
legenda numa região vazia (1700–2800 cm⁻¹), `merge=50` cm⁻¹ (pico a menos de 50 cm⁻¹ de um já rotulado é pulado).
Referência de uso: `work_turbomole/azobenzeno/project_state/figures/deck/gen_figs.py` (bloco "4. IR").

## Slides (regra de legibilidade, 2026-10-16)

Em figura para slide, use `peak_labels(..., max_cats=1)`: só a categoria dominante (`γ(C–H)`, `ring oop`), porque dois termos em 24 px ocupam quase toda a altura do eixo. A explicação dos rótulos vai para o texto do slide. Os rótulos do artigo continuam com duas categorias (`max_cats=2`, padrão).
