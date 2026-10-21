---
name: research-paper-writing
description: Improve academic paper writing quality with clear section structure, paragraph flow, and reviewer-facing presentation; for the user's computational chemistry/physics papers (Turbomole/VASP/CP2K, revtex) it enforces the user's style (combined Results and Discussion, every figure discussed in flowing prose, user's paragraphs preserved). Use when drafting or revising Abstract, Introduction, Related Work, Method, Experiments, or Conclusion; polishing figures/tables; checking claim-support alignment; or performing self-review before submission.
---
# Research Paper Writing

## User style first (overrides everything below)

For the user's own papers (computational chemistry/physics, revtex; e.g. artepillin C Paper 1/2), **read
`references/user-style-comp-chem.md` before writing** and follow it over the generic ML guidance in this file.
Core points (rejected rewrite, 2026-10-15):
- **"Results and Discussion" is one section**: present the data and discuss it in the same flowing paragraphs.
  Never a separate Discussion section, never `\emph{Discussion.}` paragraphs.
- **Discuss every figure**: introduce it, walk the panels with numbers (from the data files), interpret, give the
  caveat, link to the next result.
- **Formal, flowing prose** with connectives (Consequently, Furthermore, In this context, Nevertheless, ...);
  hedged claims; no telegraphic sentences.
- **Figure text size**: text inside images must print at the body-text size after compilation (10 pt); a figure scaled down in the layout (e.g. 178 mm grid at `\columnwidth`) fails this. Details in `references/user-style-comp-chem.md` §0.
- **Preserve the user's paragraphs** (Abstract/Introduction/Methods untouched unless asked); increment, do not
  replace. Keep `\todo/\pending/\open` markers; contradictions with the data become `\todo{}` + a note in the chat.
- The Output Contract below (outline, paragraph roles, checklists, claim-evidence map) goes **in the chat**, never
  into the manuscript.

## Versioning (mandatory for every `.tex` of the user's papers, incl. `supp_*.tex`; rule set 2026-10-21, dotted scheme confirmed by user)

Applies to the main text and the supplement (e.g. `paper_2.tex`, `supp_paper_2.tex`), living in the paper root
(e.g. `artepillin_C_studies/paper_2/`). The working file in the root always carries the latest version in its name.

**Naming:** `<stem>_v<MAJOR>[.<PENDING>.<TODO>].tex`, dotted fields so counts may exceed 9:
`paper_2_v1.tex`, `paper_2_v1.1.1.tex`, `supp_paper_2_v2.10.12.tex` (10 pendings and 12 todos since v2).
- **MAJOR** (integer) +1 whenever something new is added, removed or restructured (relevant text, discussion,
  sections, figures/tables). The other two fields reset: v1.3.5 -> v2 (written without the `.0.0`).
- **PENDING** +1 for each `\pending{}` resolved.
- **TODO** +1 for each `\todo{}` inserted **or** resolved.
- Both fields are always written together once either is nonzero (`v1.0.2`, `v1.3.0`), never `v1.2`.
- Counts accumulate from the previous version (v1.1.1 + one more pending -> v1.2.1).
- If a round mixes structural change with pending/todo work, the major bump wins (other fields reset).

**Procedure (never skip, before touching the file):**
1. Copy the current file as is (same name, version included) to `old/` in the paper root (`mkdir -p old`). Never
   overwrite or edit anything in `old/`; if the name already exists there, stop and ask.
2. Edit the root file in place.
3. When done, `mv` it to the new name per the rules above, then tell the user: previous -> new version and the
   tally (e.g. "2 pendings + 1 todo resolved, 1 todo inserted -> v1.2.2"). Check that no other file (`\input`,
   scripts, plan docs, `CLAUDE.md`) still points to the old filename and update the references.
4. If the root file is still unversioned (e.g. `paper_2.tex`), step 1 copies it to `old/` under that name and the
   first renamed result is `<stem>_v1...` (or `_v2` if the round is structural), as above.

## Overview

Use this skill to rewrite a research paper into a reviewer-friendly, high-clarity draft.
Prioritize first-impression quality (figures/tables/layout), logical flow, and evidence-backed claims.

## Core Workflow

1. Clarify the paper story before sentence-level edits.
2. Use section-specific guidance in `references/`.
3. Rewrite paragraph-by-paragraph with one message per paragraph.
4. Run reverse outlining after writing each section.
5. Check every major claim in Abstract/Introduction against experimental evidence.
6. Run final-paper adversarial review with `references/paper-review.md`.

## Global Principles

1. Keep one paragraph for one message only.
2. State the paragraph message in the first sentence.
3. Make nouns self-contained; define new terms before reusing them.
4. Maintain sentence-to-sentence flow (cause, contrast, consequence, or refinement).
5. Iterate with adversarial self-review: read as a skeptical reviewer.
6. Treat visual quality as core content, not decoration.
7. Use a clean teaser and pipeline figure.
8. Use readable, minimal-ink tables.
9. Keep formatting consistent and tidy.

## Paragraph Clarity Check (Important)

Use this quick test whenever the user asks whether a paragraph "flows" or is clear.

1. Read as an external reader:
   - Does this paragraph have one explicit message?
   - Does the first sentence state what this paragraph will do?
   - Are all key nouns/terms readable without hidden context?
   - Does each sentence connect to the previous one with a clear relation (cause, contrast, consequence, refinement, example)?
2. Run reverse outlining for the current section:
   - Write down thesis/main claim.
   - Write down each paragraph topic sentence.
   - Write down the evidence/explanation points under each paragraph.
   - Check mapping: topic sentence -> thesis, and evidence -> topic sentence.
   - Revise or remove any paragraph that cannot be mapped cleanly.
3. If flow is still weak, add temporary section headers and explicit transition phrases during revision, then remove unnecessary headers before finalizing.

Source reference for this check:

- `references/does-my-writing-flow-source.md`

## Section Guides

Load only the needed section file:

- **User's comp-chem papers (load first, overrides the rest)**: `references/user-style-comp-chem.md`

- Introduction: `references/introduction.md`
- Abstract: `references/abstract.md`
- Related Work: `references/related-work.md`
- Method: `references/method.md`
- Experiments: `references/experiments.md`
- Conclusion: `references/conclusion.md`
- Paper review (Paper Review): `references/paper-review.md`
- Paragraph clarity source: `references/does-my-writing-flow-source.md`
- Example bank index: `references/examples/index.md`

## Paper Review Core Points

Use `references/paper-review.md` for the full checklist and workflow.

1. Add an end-of-draft self-review question list in five dimensions:
   - contribution,
   - writing clarity,
   - experimental strength,
   - evaluation completeness,
   - method design soundness.
2. Treat claim-evidence alignment as a hard constraint, especially for Abstract and Introduction.
3. Perform adversarial writing: review as a skeptical reviewer and resolve every high-risk question.
4. Revise until major rejection risks are explicitly addressed.

## Execution Rules

1. Build a mini-outline before drafting prose.
2. For each subsection, explicitly include motivation, design, and technical advantage when applicable.
3. Avoid writing style that looks like incremental patching of a naive baseline.
4. Keep terminology stable across the full paper.
5. If a claim cannot be supported by results, weaken or remove the claim.
6. Before finalizing, append and answer a five-dimension self-review question list, then revise the paper based on unresolved items.
7. Do not load all section references (Introduction/Abstract/Related Work/Method/Experiments/Conclusion) at once; load only the specific section guide needed for the current edit target.

## Output Contract

When asked to rewrite or draft sections, return:

1. A compact section outline (3-7 bullets).
2. Revised paragraphs with explicit paragraph roles (opening/challenge/method/advantage/evidence/limitation).
3. A short self-review checklist covering clarity, flow, terminology consistency, unsupported claims, and missing evidence.
4. A claim-evidence map for each major claim in the revised text using `Claim: ... | Evidence: ... | Status: supported/needs evidence`.
