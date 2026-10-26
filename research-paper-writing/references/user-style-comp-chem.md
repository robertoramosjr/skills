# User writing style (Roberto): computational chemistry / physics papers

This file **overrides** the generic ML/CV/NLP guidance of this skill whenever the
paper is one of the user's (Turbomole/VASP/CP2K, revtex, molecules or materials).
Models: `paper_1.tex` (published-style Results and Discussion) and the user's
`paper_2.tex` (Introduction, Methods). Read a few paragraphs of the user's own
paper before writing anything.

Origin (2026-10-15): a rewrite of Paper 2 that split each result into a short
"data" paragraph plus a separate `\emph{Discussion.}` paragraph, in terse
sentences, was rejected. The user wants data and discussion together, flowing
prose, and every figure discussed.

## 0. Font size in figures (mandatory, checked on the compiled PDF)

- Text inside an image (labels, tick numbers, legends, panel letters, NTO/grid
  annotations) must print at the **same size as the body text** of the paper
  after compilation (revtex4-2 `aps,prb` default: 10 pt body; check the
  `\documentclass` options if the class changes).
- Printed size = source font size x (printed width / source width). A figure
  rendered at 178 mm and included at `\columnwidth` (~86.7 mm) prints at ~0.49x:
  a 10 pt label becomes ~4.9 pt. Fix the geometry, not only the font: render at
  the width it will be printed at, or include it at `\textwidth` in a
  `figure*` environment.
- Check every new or changed figure: compute the scale factor from the
  `\includegraphics` width and the source width, then confirm the label size.
- **Why:** rule added 2026-10-20 after the NTO grids (main and SM) printed with
  unreadable labels.

## 1. Structure

- **"Results and Discussion" is one section.** Never split into Results +
  Discussion, never add a separate "Discussion" section, never label paragraphs
  `\emph{Discussion.}`.
- Open the section with a short roadmap paragraph ("The results are presented
  following the logic of the computational workflow. ... are discussed first,
  ... are then examined, ... Finally, ...").
- Subsections follow the workflow (ensembles → level of theory → models →
  audit → spectra → thermodynamics → experiment → robustness). Descriptive
  titles are welcome, also as statements ("Geometry convergence is not a
  formality for this molecule").
- Conclusions come after Results and Discussion. If the user left a `\todo` in
  the Conclusions (e.g. "write after W4"), keep it.

## 2. Discuss every figure (pattern)

For each figure or table, in this order, in continuous prose:
1. **Introduce it**: "Figure~\ref{x} summarizes/compares/shows ...".
2. **Walk the panels with numbers**: "(Fig.~\ref{x}a) ... whereas in
   Fig.~\ref{x}b ...". Read the values from the data file (CSV/.dat), not by
   eye, whenever a file exists; say "about" when reading from the plot.
3. **Interpret**: what the pattern means physically/chemically ("This
   indicates that ...", "The origin of this behaviour is ...").
4. **Caveat / scope**: "It should be noted, however, that ...", "This ...
   should not be interpreted as ...", "although with only N = 11 ...".
5. **Link** to the next result or to another section ("a point we return to
   in Sec.~\ref{...}", "which anticipates ...").

Enumerations inside prose are part of the style: "Three features stand out.
First, ... Second, ... Third, ...", "Two further points are worth recording."

## 3. Register and sentences

- Formal, complete, flowing sentences of medium to long length; connectives at
  the start of sentences: *Consequently, Furthermore, In addition, In this
  context, Nevertheless, However, In contrast, Accordingly, Motivated by these
  considerations, Particular attention is devoted to, Taken individually, ...*.
- First person plural ("we") is fine in Results; passive voice dominates in
  Methods ("Conformational sampling was performed ...").
- Hedge claims to the evidence: *indicates, suggests, is consistent with, may
  reflect*. Strong verbs only for what a control actually showed.
- Numbers with `siunitx` (`\SI{}{}`, `\si{}`), states and methods named
  consistently with the user's text (N, A, B, D; HSE06-D3(BJ)/def2-TZVP; r$^2$SCAN-3c).
- **Avoid** (the rejected style): telegraphic one-line sentences, slogans
  ("The cut must be made in water." as a standalone paragraph opener is the
  user's, but do not multiply them), bullet-like prose, removing the user's
  connectives to "tighten" text.

## 4. Editing the user's text

- **Preserve the user's paragraphs**; increment around them. Do not rewrite the
  Abstract, Introduction or Methods unless explicitly asked. Keep the user's
  source formatting (e.g. short lines in Methods), header comments and markers.
- Draft markers: `\todo{}` (missing text/decision/citation), `\pending{}`
  (number that changes after a running stage), `\open{}` (data owed by the
  experimental group). Keep them; add new ones instead of guessing.
- When the data contradict a sentence of the user, **do not silently change it**:
  add a `\todo{}` next to it with the value from the file and the file name,
  and report it in the chat.
- Do not "fix" citation keys you cannot verify; list missing keys in the chat.

## 5. Supplemental Material (style of `supp_paper_1.tex`)

- **Regra de destino (decisão do usuário, 2026-10-16):** tabelas, dados e análises de caráter
  *complementar à discussão* (checagens de robustez, números absolutos que apoiam mas não
  são o argumento, resultados de reserva para perguntas de referee) vão **sempre** para o
  SM, e o texto principal **sempre** os cita ("Table~S\ref{...} of the Supplemental Material"
  / `Sec.~S...`) numa frase que diga o que o leitor encontra lá. Nunca deixar material
  complementar só no principal, nem no SM sem referência no principal.
- Opening paragraph that maps the SM sections.
- Every table has **explanatory prose before it** (what to look at, two or three
  observations), and a LaTeX comment naming the source file
  (`% source: Figures/data/...`).
- Fill tables from the data files; leave `\todo{}` only for what does not exist.
- Hard-coded references to main-text figures/tables ("Fig.~4c of the main
  text") must be checked against the compiled `.aux` after any figure is added
  or moved. revtex numbers main-text tables with Roman numerals (Table~I).
- Wide tables (> ~5 numeric columns or long names): `table*`.

## 6. Checks before delivering

- Compile (`latex`+`bibtex`, user TeX Live; see the project CLAUDE.md), zero
  errors; list undefined citations.
- Render the pages with new figures/tables (`dvips`→`ps2pdf`→`pdftoppm -r 60`)
  and look at them.
- In the chat (not in the paper): list the contradictions found between text,
  figures and data files, and the new `\todo{}` items.

## 7. Relatórios (pós-doc, de andamento) — registrar fatos, não decisões (regra do usuário, 2026-10-26)

Vale para relatórios como `relatório_posdoc/` (capítulos em `Files/capN_001.tex`), que acompanham
testes em andamento. Diferem do paper: o texto **reporta o que foi feito e medido**, na ordem em que foi feito.

- **Não registrar o motivo de decisões de rumo** (por que algo foi adiado, descartado, priorizado ou
  deixado para depois). Exemplo removido: "a estratégia de aprendizado ativo ... foi adiada, pois só
  faz sentido quando o modelo já tem erro baixo". Decisão e justificativa vão para o cofre/plano ou
  para o chat, nunca para o relatório.
- Permitido: método, parâmetros, resultados com números, interpretação do dado (hipóteses ligadas à
  evidência, com ressalva), e o que **ainda não foi feito** como `\pending{}`/`\todo{}`.
- Ao escrever ou revisar, procurar frases do tipo "foi adiado/descartado/optou-se por ... porque",
  "como consequência, decidimos", "não faz sentido ainda"; se for decisão sem dado, apagar; se houver
  dado que a sustenta, manter só o dado.
- O usuário edita no Overleaf; o que ele removeu lá deve ser removido também na cópia local (manter
  as duas coerentes). Alterações são feitas nos arquivos segmentados de `Files/`.
- **Why:** pedido do usuário em 2026-10-26 ao remover a frase sobre aprendizado ativo do cap. 5.
