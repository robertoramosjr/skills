# Pitfalls and how to avoid them (paper figures)

Lessons from real figure work (Paper 2 re-plot, 2026-10-15). Each entry: the trap, then the rule that prevents it.

## 1. Layout units
**Trap:** a Veusz-style layout written in cm was passed to a helper that assumed mm. Every panel shrank to 1/10 of the page and the labels overlapped.
**Rule:** one helper converts all layout coordinates; state the unit in its name or docstring (`*_cm`, `*_mm`). After each build, look at the PNG: no panel should occupy less than about half of the figure area.

## 2. Legend or annotation on top of data
**Trap:** `loc="lower right"` was chosen without looking at the data, so the legend covered curves.
**Rule:** before fixing a legend or note position, look for the empty corner of the data (for monotone curves, the corner away from the trend; for scatter clouds, the corner with no points). Use `bbox_to_anchor` to pin it there, and check the PNG. Statistics notes (ρ, Q², p) go in the corner opposite the cloud.

## 3. Panel labels
**Rule:** labels are `a)`, `b)`, `c)`, bold, placed by one helper (`letter(ax, "a")`). Never write the label inline in each panel: a format change then needs one edit.

## 4. Fonts (serif Times, user preference)
**Trap:** "Times New Roman" is missing on Linux, so matplotlib silently falls back to DejaVu.
**Rule:** `font.family="serif"`, `font.serif=["Times New Roman","Times","Liberation Serif","Nimbus Roman","STIX"]`, `mathtext.fontset="stix"`. Check what was used with
`matplotlib.font_manager.findfont("Times New Roman", fallback_to_default=False)` or by listing `fontManager.ttflist`. Liberation Serif is metric-compatible with Times, so it is an acceptable substitute; say so in the report.

## 5. EPS and LaTeX
**Trap:** `pdflatex` cannot include `.eps` files. The manuscript used `\includegraphics{...pdf}`, so an EPS-only export breaks the build.
**Rule:** either compile with `latex` + `dvips`/`dvipdf`, or add `epstopdf` (package `epstopdf-pkg`) to the preamble, or keep a `.pdf` companion next to every `.eps`. Compile once with the real toolchain before sending.

## 6. Raster hidden inside EPS
**Trap:** transparency (`alpha`) or `rasterized=True` embeds a bitmap in the EPS, and the file looks fine on screen.
**Rule:** keep `alpha` out of EPS figures. Quick heuristic: `grep -a -c "colorimage\|/ImageType" file.eps` should be 0. This is a heuristic, not a proof; `check_export.py` checks DPI and `pdf.fonttype` only, not `ps.fonttype`, so set `ps.fonttype=42` by hand.

## 7. Categorical series
**Rule:** for a series over categories (states, methods), use markers joined by a thin line (`lw≈0.9`, marker ≈3 pt). Isolated dots hide the trend.

## 8. Data logic: one source
**Trap:** copying the data-extraction code from the Veusz builder into a second script let the two diverge.
**Rule:** import the helpers from the original builder (`from plot_<project>_figures import read_csv, sdir, ...`) so both renderings read the same files. Run with `LC_ALL=C`, and resolve `--project-root` relative to the script (`../..` from `scripts/`).

## 9. Verification loop
**Rule:** build → open the PNG → fix → rebuild. Then run `check_export.py` and `check_fontsize.py` on the script. Do not claim a layout is fixed without looking at it.

## 10. Images that do not arrive
**Trap:** the user sent screenshots that reached the session only as a coordinate note, without the image. Acting on guesses about them wastes rounds.
**Rule:** if a message says "image" and no image is visible, say so and ask for a re-attachment or a text description. Verify with a local render instead.

## 11. Where the figures live
**Trap:** the project folder was outside the git repository the user linked, so pushing that repo did not show the figures.
**Rule:** before promising a link, confirm which repository tracks the figure folder (`git -C <dir> rev-parse --show-toplevel`). Do not commit unrelated uncommitted work in that repo; commit only the figure files, or ask first.
