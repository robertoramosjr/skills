# Structure renders (3D molecular figures, VESTA style)

Ball-and-stick figures of molecules from `.xyz` files: one figure per structure, plus labelled grids of conformer ensembles. Reference implementation: `scripts/render_structures.py` (copy of the Paper 2 script; edit the `STATES`/`ENSEMBLES` maps and paths for a new project).

## Format rule (exception to "vector EPS")
Shaded 3D renders are true raster content. Deliver a **600 dpi PNG** and an **EPS that wraps it** (PostScript level 3, lossless Flate). Keep the editable sources next to them: `.pov` (POV-Ray scene) and `.vesta` (VESTA file).

| Output | Purpose |
|---|---|
| `<name>.png` | 600 dpi render, width = print width |
| `<name>.eps` | manuscript file (PNG inside, Flate, physical size in the BoundingBox) |
| `<name>.pov` | editable POV-Ray scene |
| `<name>.vesta` | editable VESTA file (user fine-tuning) |

Widths: print width of the journal column — 86 mm single structure / 178 mm grids for revtex APS (89 / 183 mm for Nature-family). No frame, no axes: the closed-frame rule applies to plots, not to structure renders.

## Style (user's VESTA look)
| Element | Colour | POV-Ray radius (Å) | VESTA radius (Å) |
|---|---|---|---|
| H | `#1818f9` (blue) | 0.17 | 0.46 |
| C | `#f98e21` (orange) | 0.30 | 0.77 |
| O | `#f8211f` (red) | 0.28 | 0.74 |

- Bonds: cylinders r = 0.10 Å, split at mid-length, each half in its atom's colour; bonded if d < 1.2 × (sum of covalent radii).
- White background, no axes, no labels on single structures.
- Finish: `ambient 0.25 diffuse 0.75 specular 0.3 roughness 0.01 phong 0.9 phong_size 90`; key light 1.0 upper-left-front, fill light 0.25 shadowless. This gives the sharp white highlight of VESTA.
- Colours sampled from a VESTA render; other elements: sample the same way (sphere body, away from the highlight).

## Orientation
1. Normal of the best-fit plane of **all atoms** (smallest-variance axis) along the view axis: chains open, nothing stacked in depth.
2. First principal axis of the heavy atoms horizontal.
3. A characteristic group of the molecule on the right (choose one per project and keep it fixed; in the reference script: the carboxyl carbon, C bonded to two O); rotate 180° about the view axis if needed. Edit `orient()` for another molecule.
Same rule for every structure, so states are comparable. The user changes the view in `.vesta`/`.pov`.

## Conformer grids
- One PNG per conformer (+ `.pov`, `.vesta`) in `ensembles/<state>/conf_NN`, then one grid per state.
- **Same scale in every cell**: one common view window = the largest extents of all conformers of that state.
- 5 columns (2 rows for 10 conformers); fewer conformers → one row. 600 dpi, same as single structures.
- Label `conf N` above each cell, Times (Liberation Serif) at **10 pt print size** (`font_px = 10/72 × dpi`). Populations go in the caption or a table, not in the cells.
- Legend row under the grid: one sphere per element with its symbol.

## Commands
```bash
conda create -y -n render_env -c conda-forge python=3.11 povray ase pillow numpy   # once, no root
~/.conda/envs/render_env/bin/python scripts/render_structures.py --states N A B D            # single structures, 86 mm
~/.conda/envs/render_env/bin/python scripts/render_structures.py --ensembles --states N A B D # grids, 178 mm
```

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Orange renders as tan, colours washed out | POV-Ray treats `rgb` as linear light and gamma-encodes output | convert sRGB hex to linear before writing the `.pov` |
| `orthographic` keyword fails to parse (POV-Ray 3.7 conda build) | build quirk | perspective camera 1000 Å away with explicit `angle`, `right`, `up` (parallax < 0.5 %) |
| EPS of 15–20 MB | PIL writes uncompressed EPS | write the EPS directly: zlib + ASCII85, `/FlateDecode` image, level 3 |
| `gs eps2write` with `ColorImageFilter=/FlateEncode` → rangecheck | Ghostscript 9.27 only offers lossy JPEG there | do not use `eps2write` for this; use gs only to validate (`-sDEVICE=nullpage`) |
| Atoms tiny in VESTA | VESTA draws ball-and-stick at 0.4 × the stored radius, and reads `STRUC` as fractional coordinates | store VESTA default radii (H 0.46, C 0.77, O 0.74); write a P1 box (`CELLP`, extent + 10 Å) with fractional coordinates |
| Prenyl/alkyl chains stacked in depth | ring plane used as the view plane | use the best-fit plane of all atoms |
| Molecules small inside grid cells | common scale across conformers (intended) | accept, or use fewer columns |

## Verification
- Render one structure first and compare it side by side with the user's reference (colours, H/C/O size ratio, highlight) before rendering the rest.
- PNG width = round(width_mm / 25.4 × dpi); EPS passes `gs -sDEVICE=nullpage`.
- Round-trip check: rasterise the EPS back at the same dpi and compare with the PNG (mean difference ≈ 0).
- The user opens one `.vesta` to confirm (VESTA is not available on the cluster).
