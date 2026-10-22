# Apresentações de resultados científicos (regras do Roberto)

Vale para qualquer deck que mostre **resultados de cálculos** (Turbomole, VASP, CP2K). Ler antes da Phase 3.
Origem: pedido de 2026-10-16 no deck do azobenzeno (`work_turbomole/azobenzeno/apresentacao_resultados/`), que é o exemplo de referência.

## Regras

1. **Escopo:** mexer só no que o usuário pediu. Não remover nem reescrever slides por conta própria (ele já corrigiu isso: "eu falei só do 4").
2. **Todo resultado quantitativo é comparado com a literatura**, numa tabela pequena ao lado da figura, com a linha "nosso" destacada (`tr.us`). Incluir experimento e teoria de alto nível (CC2, CASSCF, CC3) quando existirem, e dizer a diferença ou a tendência em uma frase.
3. **Referências em todo deck de resultados:** citação curta numerada `[n]` no ponto de uso, fonte no rodapé do cartão e **slide final "Referências"** com a lista completa (autores, revista, volume, página, ano; DOI quando verificado).
4. **Verificar antes de citar. Nunca de memória.** Número só entra se foi lido na fonte. Sem dado verificado, escrever que não há (ex.: "sem espectro experimental do cis verificado") e apontar onde procurar.
5. **Padrão por tipo de resultado:**
   - **Gap HOMO-LUMO:** referência com o gap dos dois isômeros/estruturas, em mais de um funcional; comparar o sinal da diferença, não o valor absoluto (GGA subestima).
   - **DOS/PDOS:** referência de DOS/PDOS já calculados (gás e, se houver, superfície); comparar o caráter dos orbitais de fronteira e qual átomo domina os picos.
   - **Óptico:** tabela S₁/S₂ com experimento, RI-CC2 e um híbrido de longo alcance ao lado do nosso funcional; dizer o erro em eV por estado.
   - **IR:** a figura rotula os **5 picos mais intensos** com o modo (só o caráter, sem o número de onda, de `academic-figure-skill/scripts/ir_mode_assign.py`); bandas fortes do experimento contra as nossas, com o desvio em %. Harmônico sem escala fica 2 a 5 % acima do experimento. Experimento gás: NIST WebBook (JCAMP, ver abaixo).
   - **Bond order / carga:** uma referência que corrobora (distâncias de ligação são a ponte natural com SEN) e um bloco **"O que isso muda na molécula"** com a consequência estrutural, eletrônica e espectroscópica. Marcar o que é interpretação nossa.
   - **Geometria/RDF:** bloco **"Sugestão · o que isso implica"**, rotulado como sugestão (verde), com uso prático no projeto.
6. **(Opcional; no azobenzeno foi removido em 2026-10-22 por redundar com "Próximos passos")** Antes do slide de referências, um slide "O que estamos fazendo" ligando cada item do "o que falta/próximos passos" ao andamento real. Fonte: `python3 ~/cofre/tools/cofre.py start <projeto>`, **mais `squeue`/`sacct`**: job `PENDING` é "na fila", não "rodando". Resultado de piloto sai com o n e a ressalva ("n = 10, não é rendimento quântico").
6b. **"O que fizemos / o que falta" NÃO é pedido literal; é pedido de CONCLUSÕES + PRÓXIMOS PASSOS (regra do Roberto, 2026-10-22: "se não, de nada me adianta").** Quando ele pedir esse slide com essas palavras (ou "próximos passos", "o que sai daqui"), não faça um inventário de tarefas feitas e pendentes. Faça o que ficou aprovado no deck do azobenzeno (slide 11, "Conclusões"):
   - **Título = afirmação**, não rótulo (ex.: "O protocolo vale para estrutura e ligação; para a luz, o nível de teoria muda").
   - **Duas colunas (`.grid2` + `.card` + `.notes.tight .note`)**: esquerda **"O que concluímos"** (4 notas: método validado contra a literatura; nível de teoria a usar para cada propriedade e por quê; decisões de método, ex. PDOS Becke/SCPA; diferença física entre as estruturas comparadas); direita **"Próximos passos"** numerados, derivados do **objetivo vigente do projeto** (ler a nota do cofre com `cofre.py start <proj>` e o plano em `docs/plans/`; o objetivo muda, não reaproveitar os passos do deck anterior), cada um com critério de decisão quando existir ("≥ 80 % no azo = localizado; senão, o contato desliga a fotocomutação").
   - Só conclusão sustentada pelos slides anteriores; ressalvas de método entram como parte da conclusão, não como nota solta.
   - O slide "O que estamos fazendo" (regra 6) só existe se trouxer algo além dos próximos passos; se repetir, avisar o usuário em vez de apagar (regra 1).
   - **Clique que troca o conteúdo de um cartão** (usado para justificar uma escolha, ex. por que a âncora –SH/–NH₂): `<section data-steps="1">`, cartão `.card.flip` com camadas `.l1` (texto) e `.l2` (figura, `position:absolute`); o controlador do deck avança o passo com seta/espaço/clique antes de trocar de slide. `export-pdf-pptx.py` gera uma página extra por passo (`?step=k`). Figura do clique = esquema rotulado como tal ("estrutura real" × "esquema"), 18 pt = 24 px.

7. **Sempre entregar HTML + PDF + PPTX** (ver `scripts/export-pdf-pptx.py`). Se o cluster não tem Chromium/LibreOffice, o script usa Firefox headless. O PPTX é imagem por slide, com o texto nas notas.
8. **A figura preenche a janela branca (`.plate`), sem faixas brancas sobrando.** Figuras de artigo (183 mm de largura, proporção ~1,8 a 3:1) numa janela mais alta ficam menores e com margem; isso incomoda. Gere uma **variante de slide** com a proporção da janela (receita abaixo) e deixe a figura do artigo intacta.
9. Conferir no render: nada estoura o cartão, nada cobre o rodapé. Na dúvida, fonte ≥ 24 px (palco 1920×1080).

## Como verificar referências (receita que funcionou)

1. `WebSearch` para achar a referência; `WebFetch` no resumo (arXiv `abs`, página do grupo) para volume/página/DOI.
2. Valores numéricos: **baixar o PDF aberto** (`curl -sL https://arxiv.org/pdf/<id> -o x.pdf`; `pdftotext -layout x.pdf x.txt`; `grep` nas tabelas). WebFetch não lê PDF binário.
3. Números que só existem em figura (ex.: comprimentos de ligação na Fig. 1 do Cembran): `pdftoppm -f <pág> -l <pág> -r 130 -png` e olhar a imagem.
4. Dado experimental citado por um artigo de teoria: citar o artigo que você leu e listar as fontes primárias dele na mesma entrada ("exp.: Andersson 1982; Biancalana 1999").
5. IR experimental de gás: `curl -sL "https://webbook.nist.gov/cgi/cbook.cgi?JCAMP=C<CAS sem hífen>&Index=0&Type=IR"` e extrair os máximos do JCAMP (XYDATA, `YFACTOR`, `DELTAX`, `FIRSTX`). `Index=0` é o espectro de fase gasosa do NIST.
6. Conferir o periódico publicado de preprints arXiv (a página `abs` traz `Journal reference`).

## Componentes CSS (copiar para o `<style>`)

```css
.lit{background:var(--card);border:1px solid var(--rule);padding:20px 26px;display:flex;flex-direction:column;gap:9px}
.lit .k{font-family:var(--f-mono);font-size:20px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.lit p{font-size:26px;line-height:1.28}
.lit table{font-size:26px;width:100%}
.lit th{font-size:19px;padding:6px 8px;letter-spacing:.06em}
.lit td{padding:7px 8px;font-size:26px}
.lit td.m{font-family:var(--f-mono);font-size:24px}
.lit tr.us td{background:rgba(27,31,42,.07);font-weight:600}   /* nosso resultado */
.lit .src{font-family:var(--f-mono);font-size:20px;color:var(--muted);line-height:1.3}
.lit.sug .k{color:#1E7A4C} .lit.sug p{font-size:29px}            /* sugestão / o que muda */
.ref{font-family:var(--f-mono);font-size:.62em;vertical-align:super;color:var(--muted);margin-left:2px}
.notes.tight{gap:16px;justify-content:flex-start}
```

Padrões de layout que couberam em 1920×1080:
- **Figura + notas + cartão de literatura:** coluna direita de 640 a 700 px (`.notes.tight`) com os resultados nossos e o `.lit` embaixo. A figura é limitada pela altura, então alargar a coluna não custa nada.
- **Figura larga (óptico, RDF):** `row` com `plate` (flex:1, `min-height:0`) + cartão de 700 px à direita, e a faixa `.strip` de notas embaixo.
- **Slide com muita coisa (bond order):** placa de 800 px e coluna com dois cartões (tabela de literatura + "o que muda").
- **"O que estamos fazendo":** grade 2×2 de `.card` com `h3`, `.chip` de status (`done`/`run`/`wait`) e parágrafo de 32 px.
- **Referências:** `ol.refs` com `[n]` em mono, 31 px.

## Figura que preenche a janela (validado no deck do azobenzeno, 2026-10-16: slides 4 a 9)

1. **Meça a janela branca (`.plate`) no render**, não estime: screenshot 1920×1080, máscara de branco puro (`min(R,G,B) >= 253`), retângulo. Cuidado: a moldura do gráfico parte o branco em regiões, então `scipy.ndimage.label` pode pegar só uma delas; limite a caixa de busca às colunas da janela e use o bbox de todo o branco. A proporção-alvo da figura é a da janela menos o padding (use `padding:10px`).
2. **Script de figuras com modo slide.** No `gen_figs.py` (matplotlib):
   ```python
   SLIDE = os.environ.get("SLIDE") == "1"
   SLIDE_AR = {"fig_x": largura/altura, ...}      # calibrado, ver passo 3
   def fs(w_mm, h_mm, name): return (w_mm/25.4, (w_mm/SLIDE_AR[name] if SLIDE and name in SLIDE_AR else h_mm)/25.4)
   def save_cns_figure(fig, filename):
       if SLIDE:                                     # só PNG, nome <fig>_slide.png
           if os.path.basename(filename) in SLIDE_AR: fig.savefig(f"{filename}_slide.png", bbox_inches="tight", dpi=300)
           return
       fig.savefig(f"{filename}.eps", ...); fig.savefig(f"{filename}.png", ...)   # artigo, inalterado
   ```
   e em cada figura `plt.subplots(..., figsize=fs(183, 62, "fig_x"))`.
3. **Calibre em 2 a 3 iterações:** `bbox_inches="tight"` muda a proporção final. Rode `SLIDE=1`, leia o aspecto real do PNG e faça `AR *= alvo/real` até o erro ser < 1 %. Grave os valores calibrados como padrão no script.
4. HTML: `<div class="plate" style="flex:1;min-height:0;padding:10px"><img src="img/fig_x_slide.png"></div>` (`min-height:0` em toda janela, para a imagem não empurrar o layout).
5. Rode também **sem** `SLIDE` e confirme por `md5sum` que os PNGs do artigo não mudaram (os EPS mudam de bytes por regravação: restaure os antigos de um backup).
6. Remeça as janelas depois de aplicar e olhe o render. Janelas ao lado de cartão de literatura ficam ~1,4 a 1,8:1; faixa de largura total fica ~3,4:1. Painéis 1×3 numa janela 1,7:1 saem altos e estreitos, o que é aceitável; se incomodar, mude o layout (cartão embaixo), não a figura.

## Texto da figura = texto do slide (regra do Roberto, 2026-10-16)

A figura do slide é lida no palco de 1920 px. Se a fonte dela for menor que a do texto do slide, a legibilidade cai (no deck do azobenzeno, 6 a 9 pt viravam ~13 px contra 26 px do texto). Regra:

1. **Tamanho único = texto do slide.** No palco 1920×1080, 1 pt = 1,333 px (96 px/in). Para ficar em 24 px (tamanho das notas) use **18 pt**. Todo texto da figura (ticks, rótulos, legenda, letras dos painéis) fica em 18 pt, sem exceção.
2. **Figura desenhada na escala 1:1.** Largura da figura em polegadas = largura da janela em pixels / 96. Assim 18 pt sai com 24 px no palco, sem redução. Salve **sem `bbox_inches="tight"`** (inclusive com `rcParams["savefig.bbox"]="standard"`, porque o `tight` vem ativo por padrão no rcParams e continua valendo mesmo que você passe `bbox_inches=None`). Use só `tight_layout()`.
3. **Cabe na janela ou muda o conteúdo, nunca a fonte.** Ao aumentar a fonte, reduza o que está dentro:
   - **Legenda por painel:** uma por painel, sem título, só as entradas necessárias, `ncol=1`. Quando a mesma legenda (ex.: linha preta TDOS) se repete em todos os painéis, explique uma vez (`fig.text` no canto).
   - **Ticks:** `MaxNLocator(3)` no eixo x compartilhado.
   - **Títulos de painel:** encurte (ex.: "SCPA element" em vez de "SCPA by element").
   - **Letras a)–f):** suba um pouco acima do título.
   - **Eixo y:** deixe ~75 % de folga acima dos picos, para a legenda não cobrir dados.
4. **Rótulos com texto (IR e similares):** no slide use **só a categoria dominante** (ex.: `γ(C–H)`). Duas categorias em 24 px ocupam quase toda a altura do eixo e o eixo estica sem necessidade. A explicação dos rótulos vai para o texto do slide, não para dentro da figura (ex.: "Rótulos: 5 picos mais intensos e modo dominante (ip/oop: no/fora do plano)").
5. **Verifique no render**, não só no PNG: a figura inteira, a legenda sem cobrir dados, o rótulo sem cruzar outro e o cartão de texto sem encostar no número da página. Se o cartão de texto ficar alto, encurte um parágrafo; não reduza a fonte da figura.
6. **Figuras do artigo continuam como estão** (EPS e PNG, 183 mm, fontes de 7 a 9 pt). Só a variante `_slide.png` usa as regras acima. Confirme por `md5sum` que as do artigo não mudaram.

Implementação de referência: `work_turbomole/azobenzeno/project_state/figures/deck/gen_figs.py` (`SLIDE_PT`, `SLIDE_W`, `FS()`, `fs()`, `make_pdos()`, `annotate_ir()`).
