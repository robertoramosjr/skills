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
   - **IR:** bandas fortes do experimento contra as nossas, com o desvio em %. Harmônico sem escala fica 2 a 5 % acima do experimento. Experimento gás: NIST WebBook (JCAMP, ver abaixo).
   - **Bond order / carga:** uma referência que corrobora (distâncias de ligação são a ponte natural com SEN) e um bloco **"O que isso muda na molécula"** com a consequência estrutural, eletrônica e espectroscópica. Marcar o que é interpretação nossa.
   - **Geometria/RDF:** bloco **"Sugestão · o que isso implica"**, rotulado como sugestão (verde), com uso prático no projeto.
6. **Antes do slide de referências, um slide "O que estamos fazendo"** ligando cada item do "o que falta/próximos passos" ao andamento real. Fonte: `python3 ~/cofre/tools/cofre.py start <projeto>`, **mais `squeue`/`sacct`**: job `PENDING` é "na fila", não "rodando". Resultado de piloto sai com o n e a ressalva ("n = 10, não é rendimento quântico").
7. **Sempre entregar HTML + PDF + PPTX** (ver `scripts/export-pdf-pptx.py`). Se o cluster não tem Chromium/LibreOffice, o script usa Firefox headless. O PPTX é imagem por slide, com o texto nas notas.
8. Conferir no render: nada estoura o cartão, nada cobre o rodapé. Na dúvida, fonte ≥ 24 px (palco 1920×1080).

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
