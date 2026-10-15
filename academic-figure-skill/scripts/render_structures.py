#!/usr/bin/env python3
"""Ball-and-stick structure renders (POV-Ray PNG, EPS wrapper, POV scene, VESTA molecule file).

Usage (inside render_env):
    python scripts/render_structures.py --states A N B D

Inputs : Figures/3D_for_VESTA/{N_neutral,A_monoanion_a,B_monoanion_b,D_dianion}_top1.xyz
Outputs: Figures/3D/<input basename>.{png,eps,pov,vesta}
"""
import argparse
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image
from ase import Atoms
from ase.data import covalent_radii
import ase.io

# ---------------------------------------------------------------- style
# Colours sampled from the reference EPS raster (sphere body, lower-left of the highlight).
# Radii: r_C = 0.30 A; ratios from the reference (r_H/r_C = 0.575, r_O/r_C = 0.94).
# Bond radius: r_bond/r_C = 0.33 measured as full width ~78 px vs C radius ~120 px.
STYLE = {
    "color": {"H": "#1818f9", "C": "#f98e21", "O": "#f8211f"},
    "radius": {"H": 0.17, "C": 0.30, "O": 0.28},
    "bond_radius": 0.10,
    "bond_factor": 1.2,
    "background": "white",
    # Sharp white highlight like the VESTA reference: phong spot + weak broad specular.
    "finish": {
        "ambient": 0.25,
        "diffuse": 0.75,
        "specular": 0.3,
        "roughness": 0.01,
        "phong": 0.9,
        "phong_size": 90,
    },
    "margin": 0.10,
    "light_key": 1.0,   # key light intensity (grey level)
    "light_fill": 0.25,  # fill light intensity (grey level)
}

STATES = {
    "N": "N_neutral_top1.xyz",
    "A": "A_monoanion_a_top1.xyz",
    "B": "B_monoanion_b_top1.xyz",
    "D": "D_dianion_top1.xyz",
}

CAMERA_DIST = 1000.0  # A, see write_pov

POVRAY = os.environ.get(
    "POVRAY", os.path.expanduser("~/.conda/envs/render_env/bin/povray")
)


# ---------------------------------------------------------------- basics
def load(path):
    return ase.io.read(path)


def bonds(atoms):
    """Index pairs (i, j) with d < bond_factor * (rc_i + rc_j)."""
    d = atoms.get_all_distances(mic=False)
    rc = covalent_radii[atoms.numbers]
    n = len(atoms)
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            if d[i, j] < STYLE["bond_factor"] * (rc[i] + rc[j]):
                out.append((i, j))
    return out


def _rot_from_to(a, b):
    """Rotation matrix taking unit vector a onto unit vector b (Rodrigues)."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    s = np.linalg.norm(v)
    if s < 1e-12:
        if c > 0:
            return np.eye(3)
        # 180 deg: pick any axis orthogonal to a
        axis = np.cross(a, [1.0, 0.0, 0.0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0.0, 1.0, 0.0])
        axis = axis / np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)


def _rot_z(theta):
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def _find_ring(atoms, bond_list):
    """Return the 6 C indices of the most planar 6-membered carbon cycle."""
    numbers = atoms.numbers
    adj = {i: set() for i in range(len(atoms)) if numbers[i] == 6}
    for i, j in bond_list:
        if numbers[i] == 6 and numbers[j] == 6:
            adj[i].add(j)
            adj[j].add(i)
    cycles = set()

    def dfs(start, path):
        if len(path) == 6:
            if start in adj[path[-1]]:
                cycles.add(frozenset(path))
            return
        for nb in adj[path[-1]]:
            if nb not in path and nb > start:
                dfs(start, path + [nb])

    for s in adj:
        dfs(s, [s])
    if not cycles:
        raise ValueError("no 6-membered carbon ring found")
    pos = atoms.positions
    best, best_res = None, None
    for cyc in cycles:
        idx = sorted(cyc)
        X = pos[idx] - pos[idx].mean(axis=0)
        sv = np.linalg.svd(X, compute_uv=False)
        res = sv[-1]
        if best_res is None or res < best_res:
            best, best_res = idx, res
    return best


def orient(atoms):
    """Open view: best-fit plane of the whole molecule on screen (chains spread, as in the
    VESTA reference), long axis along x, carboxyl on the right."""
    atoms = atoms.copy()
    bl = bonds(atoms)
    pos = atoms.positions.copy()
    centre = pos[[i for i, z in enumerate(atoms.numbers) if z in (6, 8)]].mean(axis=0)
    pos = pos - centre

    # 1. normal of the best-fit plane of ALL atoms (smallest-variance axis) -> +z (view axis).
    #    This maximises the projected spread, so the prenyl chains do not stack in depth.
    X = pos - pos.mean(axis=0)
    normal = np.linalg.svd(X)[2][-1]
    R = _rot_from_to(normal, np.array([0.0, 0.0, 1.0]))
    pos = pos @ R.T

    # 2. first principal axis of heavy atoms (projected on xy) -> +x
    heavy = [i for i, z in enumerate(atoms.numbers) if z in (6, 8)]
    xy = pos[heavy, :2]
    xy = xy - xy.mean(axis=0)
    w, v = np.linalg.eigh(xy.T @ xy)
    axis = v[:, np.argmax(w)]
    theta = math.atan2(axis[1], axis[0])
    pos = pos @ _rot_z(-theta).T

    # 3. carboxyl carbon (C bonded to two O) must be on the right (x > 0)
    nb = {i: set() for i in range(len(atoms))}
    for i, j in bl:
        nb[i].add(j)
        nb[j].add(i)
    carb = [
        i for i in range(len(atoms))
        if atoms.numbers[i] == 6 and sum(atoms.numbers[k] == 8 for k in nb[i]) >= 2
    ]
    if carb and pos[carb[0], 0] < 0:
        pos = pos @ _rot_z(math.pi).T

    atoms.positions = pos
    return atoms


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _colour_rgb(el):
    """Pigment colour as LINEAR RGB (POV-Ray lights in linear space and gamma-encodes output)."""
    h = STYLE["color"][el].lstrip("#")
    return tuple(_srgb_to_linear(int(h[k:k + 2], 16) / 255.0) for k in (0, 2, 4))


def _rgb_256(el):
    """Raw sRGB 0-255 values (VESTA), not the linearised POV-Ray pigment."""
    h = STYLE["color"][el].lstrip("#")
    return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))


def _finish_str():
    f = STYLE["finish"]
    return (
        f"finish {{ ambient {f['ambient']} diffuse {f['diffuse']} "
        f"specular {f['specular']} roughness {f['roughness']} phong {f['phong']} "
        f"phong_size {f['phong_size']} }}"
    )


def _vec(p):
    return f"<{p[0]:.5f},{p[1]:.5f},{p[2]:.5f}>"


# ---------------------------------------------------------------- writers
def _half_extents(atoms):
    """Half-width/height of the oriented molecule (centred at origin) incl. atomic radii."""
    pos = atoms.positions
    radii = [STYLE["radius"][s] for s in atoms.get_chemical_symbols()]
    hx = max(abs(pos[i, 0]) + radii[i] for i in range(len(atoms)))
    hy = max(abs(pos[i, 1]) + radii[i] for i in range(len(atoms)))
    return hx, hy


def _height_px(atoms, width_px):
    hx, hy = _half_extents(atoms)
    return max(1, int(round(width_px * hy / hx)))


def _view(atoms, width_px, height_px, extents=None):
    """Orthographic window (centre, right length, up length) matching the pixel aspect ratio.
    `extents` = (hx, hy) forces a common window (same scale for every conformer of a grid)."""
    hx, hy = extents if extents is not None else _half_extents(atoms)
    m = 1.0 + STYLE["margin"]
    aspect = width_px / height_px
    hd = max(2 * hy * m, 2 * hx * m / aspect)
    wd = hd * aspect
    return 0.0, 0.0, wd, hd


def write_pov(atoms, bond_list, path, width_px, height_px, extents=None):
    """Hand-written orthographic POV-Ray scene (view down -z)."""
    pos = atoms.positions
    syms = atoms.get_chemical_symbols()
    radii = [STYLE["radius"][s] for s in syms]
    cx, cy, wd, hd = _view(atoms, width_px, height_px, extents)
    fov = math.degrees(2 * math.atan(wd / 2 / CAMERA_DIST))
    fin = _finish_str()
    lines = [
        '#include "colors.inc"',
        f'background {{ color rgb <1,1,1> }}',
        "camera {",
        # Near-orthographic: a perspective camera 1000 A away (the POV-Ray 3.7 build used
        # here rejects the orthographic keyword and an unset angle). Depth parallax is <0.5 %.
        f"  location <{cx:.5f},{cy:.5f},{-CAMERA_DIST:.1f}>",
        f"  look_at  <{cx:.5f},{cy:.5f},0>",
        f"  angle {fov:.6f}",
        f"  right <{wd:.5f},0,0>",
        f"  up <0,{hd:.5f},0>",
        "}",
        # key light upper-left-front, weak fill light
        f"light_source {{ <{cx - 30:.3f},{cy + 30:.3f},{-CAMERA_DIST / 16:.1f}> color rgb <{STYLE['light_key']},{STYLE['light_key']},{STYLE['light_key']}>}}",
        f"light_source {{ <{cx + 40:.3f},{cy - 20:.3f},{-CAMERA_DIST / 25:.1f}> color rgb <{STYLE['light_fill']},{STYLE['light_fill']},{STYLE['light_fill']}> shadowless }}",
        "",
    ]
    for i, s in enumerate(syms):
        r, g, b = _colour_rgb(s)
        lines.append(
            f"sphere {{ {_vec(pos[i])}, {radii[i]:.4f} "
            f"texture {{ pigment {{ rgb <{r:.4f},{g:.4f},{b:.4f}> }} {fin} }} }}"
        )
    lines.append("")
    rb = STYLE["bond_radius"]
    for i, j in bond_list:
        mid = (pos[i] + pos[j]) / 2
        for a, other in ((i, mid), (j, mid)):
            r, g, b = _colour_rgb(syms[a])
            lines.append(
                f"cylinder {{ {_vec(pos[a])}, {_vec(other)}, {rb:.4f} "
                f"texture {{ pigment {{ rgb <{r:.4f},{g:.4f},{b:.4f}> }} {fin} }} }}"
            )
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def render(pov, png, width_px, height_px):
    """Run POV-Ray. Returns (ok, message)."""
    cmd = [
        POVRAY, f"+I{pov}", f"+O{png}", f"+W{width_px}", f"+H{height_px}",
        "+A0.1", "+UA", "-D",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if res.returncode != 0 or not os.path.exists(png):
        return False, (res.stderr or res.stdout)[-800:]
    im = Image.open(png)
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        bg.save(png)
    return True, ""


def png_to_eps(png, eps, width_mm):
    """PNG -> EPS (PostScript level 3), image losslessly Flate-compressed + ASCII85, printed
    size = width_mm. Written directly because Ghostscript 9.27 eps2write only offers lossy JPEG
    (ColorImageFilter=/FlateEncode raises rangecheck) and PIL's EPS is uncompressed (~20 MB).
    The result is validated with Ghostscript."""
    import base64
    import zlib

    im = Image.open(png).convert("RGB")
    px, py = im.size
    w_pt = width_mm / 25.4 * 72.0
    h_pt = w_pt * py / px
    data = base64.a85encode(zlib.compress(im.tobytes(), 9), wrapcol=76) + b"~>"
    head = (
        "%!PS-Adobe-3.0 EPSF-3.0\n"
        f"%%BoundingBox: 0 0 {math.ceil(w_pt)} {math.ceil(h_pt)}\n"
        f"%%HiResBoundingBox: 0 0 {w_pt:.4f} {h_pt:.4f}\n"
        "%%LanguageLevel: 3\n%%Pages: 1\n%%EndComments\n"
        "gsave\n"
        f"{w_pt:.4f} {h_pt:.4f} scale\n"
        "/DeviceRGB setcolorspace\n"
        f"<< /ImageType 1 /Width {px} /Height {py} /BitsPerComponent 8 /Decode [0 1 0 1 0 1]\n"
        f"   /ImageMatrix [{px} 0 0 -{py} 0 {py}]\n"
        "   /DataSource currentfile /ASCII85Decode filter /FlateDecode filter >> image\n"
    )
    with open(eps, "wb") as fh:
        fh.write(head.encode("ascii"))
        fh.write(data)
        fh.write(b"\ngrestore\nshowpage\n%%EOF\n")
    res = subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=nullpage", eps],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("EPS failed Ghostscript validation: " + (res.stderr or res.stdout)[-300:])


# VESTA ball-and-stick draws atoms at 0.4 x the ATOMT/SITET radius. Its default atomic radii
# (H 0.46, C 0.77, O 0.74 A) times 0.4 give the drawn radii measured on the reference
# (C ~0.31 A), so the .vesta file stores these defaults, not the POV-Ray display radii.
VESTA_RADIUS = {"H": 0.46, "C": 0.77, "O": 0.74}


def write_vesta(atoms, bond_list, path, title):
    """VESTA CRYSTAL file: P1 box around the molecule, FRACTIONAL coordinates (VESTA reads
    STRUC as fractional), per-site radius/colour (SITET) and per-element ATOMT."""
    syms = atoms.get_chemical_symbols()
    pos = atoms.positions
    lo, hi = pos.min(axis=0), pos.max(axis=0)
    L = float(max(hi - lo)) + 10.0          # cubic box, 5 A vacuum each side
    frac = (pos - lo + 5.0) / L
    elements = []
    for s in syms:
        if s not in elements:
            elements.append(s)
    pairs = []
    for i, j in bond_list:
        pr = tuple(sorted((syms[i], syms[j])))
        if pr not in pairs:
            pairs.append(pr)
    out = ["#VESTA_FORMAT_VERSION 3.5.4", "", "CRYSTAL", "", "TITLE", title, "",
           "GROUP", "1 1 P 1", "SYMOP",
           " 0.000000  0.000000  0.000000  1  0  0   0  1  0   0  0  1   1",
           " -1.0 -1.0 -1.0  0 0 0  0 0 0  0 0 0",
           "TRANM 0",
           " 0.000000  0.000000  0.000000  1  0  0   0  1  0   0  0  1",
           "CELLP",
           f"  {L:.6f}   {L:.6f}   {L:.6f}  90.000000  90.000000  90.000000",
           "  0.000000   0.000000   0.000000   0.000000   0.000000   0.000000",
           "STRUC"]
    for k, (s, f) in enumerate(zip(syms, frac), start=1):
        out.append(f"  {k} {s:<2} {s}{k:<5} 1.0000   {f[0]:.6f}   {f[1]:.6f}   {f[2]:.6f}    1a       1")
        out.append("                            0.000000   0.000000   0.000000  0.00")
    out += ["  0 0 0 0 0 0 0", "THERI 0"]
    for k, s in enumerate(syms, start=1):
        out.append(f"  {k}  {s}{k}  0.000000")
    out += ["  0 0 0", "BOUND", "       0        1         0        1         0        1",
            "  0   0   0   0  0", "SBOND"]
    for k, (a, b_) in enumerate(pairs, start=1):
        dmax = STYLE["bond_factor"] * (covalent_radii[ase_num(a)] + covalent_radii[ase_num(b_)])
        r, g, b = _rgb_256(a)
        out.append(f"  {k}  {a}  {b_}  0.00000  {dmax:.5f}  0  1  1  0  1  0.250  2.000 {r} {g} {b}")
    out += ["  0 0 0 0", "SITET"]
    for k, s in enumerate(syms, start=1):
        r, g, b = _rgb_256(s)
        out.append(f"  {k}  {s}{k}  {VESTA_RADIUS[s]:.4f} {r} {g} {b} {r} {g} {b} 204  0")
    out += ["  0 0 0 0 0 0", "ATOMT"]
    for k, s in enumerate(elements, start=1):
        r, g, b = _rgb_256(s)
        out.append(f"  {k}  {s}  {VESTA_RADIUS[s]:.4f} {r} {g} {b} {r} {g} {b} 204")
    out += ["  0 0 0 0 0 0", "STYLE", "MODEL   2  1  0"]
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")


def ase_num(sym):
    from ase.data import atomic_numbers
    return atomic_numbers[sym]


# ---------------------------------------------------------------- ensembles (top-10 grids)
ENSEMBLES = {
    "N": "N_neutral_top10_ensemble.xyz",
    "A": "A_monoanion_a_top10_ensemble.xyz",
    "B": "B_monoanion_b_top10_ensemble.xyz",
    "D": "D_dianion_top10_ensemble.xyz",
}
FONT = "/usr/share/fonts/liberation-serif/LiberationSerif-Regular.ttf"  # Times-metric serif


def read_frames(path):
    """Multi-frame plain .xyz -> list of (Atoms, comment)."""
    frames = []
    with open(path) as fh:
        lines = fh.read().splitlines()
    k = 0
    while k < len(lines):
        if not lines[k].strip():
            k += 1
            continue
        n = int(lines[k].split()[0])
        comment = lines[k + 1]
        syms, xyz = [], []
        for ln in lines[k + 2:k + 2 + n]:
            t = ln.split()
            syms.append(t[0])
            xyz.append([float(v) for v in t[1:4]])
        frames.append((Atoms(syms, positions=xyz), comment))
        k += 2 + n
    return frames


def _element_sphere(el, path_png, size_px, extents):
    """Single sphere of element `el`, same scale/finish as the molecules (legend key)."""
    a = Atoms([el], positions=[[0.0, 0.0, 0.0]])
    pov = path_png[:-4] + ".pov"
    write_pov(a, [], pov, size_px, size_px, extents)
    return render(pov, path_png, size_px, size_px)


def process_ensemble(key, root, outdir, width_mm, dpi, ncols=5):
    """Render each conformer of a state's top-10 file, then assemble a labelled grid."""
    from PIL import ImageDraw, ImageFont

    src = os.path.join(root, "Figures", "3D_for_VESTA", ENSEMBLES[key])
    if not os.path.exists(src):
        return {"state": key, "status": "SKIPPED (missing input)", "src": src}
    base = os.path.splitext(os.path.basename(src))[0].replace("_top10_ensemble", "")
    cdir = os.path.join(outdir, "ensembles", base)
    os.makedirs(cdir, exist_ok=True)
    frames = [orient(a) for a, _ in read_frames(src)]
    n = len(frames)
    ncols = min(ncols, n)
    nrows = int(math.ceil(n / ncols))

    # one common window for all conformers -> identical scale in every cell
    ext = [_half_extents(a) for a in frames]
    common = (max(e[0] for e in ext), max(e[1] for e in ext))
    total_px = int(round(width_mm / 25.4 * dpi))
    cell_w = total_px // ncols
    cell_h = max(1, int(round(cell_w * common[1] / common[0])))
    font_px = int(round(10 / 72 * dpi))          # 10 pt at print size (body text)
    font = ImageFont.truetype(FONT, font_px)
    label_h = int(font_px * 1.4)

    cells, errors = [], []
    for i, atoms in enumerate(frames, start=1):
        stem = os.path.join(cdir, f"conf_{i:02d}")
        bl = bonds(atoms)
        write_pov(atoms, bl, stem + ".pov", cell_w, cell_h, common)
        write_vesta(atoms, bl, stem + ".vesta", f"{base} conf {i}")
        ok, msg = render(stem + ".pov", stem + ".png", cell_w, cell_h)
        if not ok:
            errors.append(f"conf {i}: POV-Ray failed (kept .pov): {msg}")
            cells.append(None)
            continue
        cells.append(Image.open(stem + ".png").convert("RGB"))

    # legend row: one sphere per element present, drawn at 2x the molecule scale for legibility
    elements = [e for e in ("C", "O", "H") if any(e in a.get_chemical_symbols() for a in frames)]
    key_px = int(round(cell_h * 0.22))
    keys = []
    for el in elements:
        kp = os.path.join(cdir, f"key_{el}.png")
        ok, _ = _element_sphere(el, kp, key_px, (STYLE["radius"]["C"] * 1.6, STYLE["radius"]["C"] * 1.6))
        if ok:
            keys.append((el, Image.open(kp).convert("RGB")))
    legend_h = key_px + label_h // 2

    grid = Image.new("RGB", (cell_w * ncols, nrows * (cell_h + label_h) + legend_h), "white")
    draw = ImageDraw.Draw(grid)
    for i, im in enumerate(cells):
        r, c = divmod(i, ncols)
        x0, y0 = c * cell_w, r * (cell_h + label_h)
        label = f"conf {i + 1}"
        tw = draw.textlength(label, font=font)
        draw.text((x0 + (cell_w - tw) / 2, y0 + label_h * 0.1), label, fill="black", font=font)
        if im is not None:
            grid.paste(im, (x0, y0 + label_h))
    # legend centred under the grid: [sphere] symbol, evenly spaced
    y_leg = nrows * (cell_h + label_h)
    slot = grid.width // max(1, len(keys))
    for k, (el, im) in enumerate(keys):
        xs = k * slot + slot // 2 - key_px
        grid.paste(im, (xs, y_leg))
        draw.text((xs + key_px + font_px * 0.4, y_leg + (key_px - font_px) / 2), el, fill="black", font=font)

    png = os.path.join(outdir, f"{base}_top10_grid.png")
    eps = os.path.join(outdir, f"{base}_top10_grid.eps")
    grid.save(png, dpi=(dpi, dpi))
    png_to_eps(png, eps, width_mm)
    return {"state": key, "base": base, "n": n, "grid": png, "eps": eps, "errors": errors,
            "size_px": grid.size}


# ---------------------------------------------------------------- driver
def process_state(key, root, outdir, width_mm, dpi):
    src = os.path.join(root, "Figures", "3D_for_VESTA", STATES[key])
    if not os.path.exists(src):
        return {"state": key, "status": "SKIPPED (missing input)", "src": src}
    base = os.path.splitext(os.path.basename(src))[0]
    result = {"state": key, "base": base, "files": {}, "errors": []}
    atoms = orient(load(src))
    bl = bonds(atoms)
    width_px = int(round(width_mm / 25.4 * dpi))
    height_px = _height_px(atoms, width_px)

    pov = os.path.join(outdir, base + ".pov")
    png = os.path.join(outdir, base + ".png")
    eps = os.path.join(outdir, base + ".eps")
    vesta = os.path.join(outdir, base + ".vesta")

    write_pov(atoms, bl, pov, width_px, height_px)
    result["files"]["pov"] = pov
    write_vesta(atoms, bl, vesta, base)
    result["files"]["vesta"] = vesta

    ok, msg = render(pov, png, width_px, height_px)
    if ok:
        result["files"]["png"] = png
        png_to_eps(png, eps, width_mm)
        result["files"]["eps"] = eps
        result["size_px"] = Image.open(png).size
    else:
        result["errors"].append(f"POV-Ray failed (kept .pov): {msg}")
    return result


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states", nargs="+", choices=sorted(STATES), default=["N", "A", "B", "D"])
    ap.add_argument("--width-mm", type=float, default=86.0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--outdir", default="Figures/3D")
    ap.add_argument("--root", default=os.path.dirname(here))
    ap.add_argument("--ensembles", action="store_true",
                    help="render the top-10 conformers of each state and assemble a grid (178 mm)")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    outdir = args.outdir if os.path.isabs(args.outdir) else os.path.join(root, args.outdir)
    os.makedirs(outdir, exist_ok=True)
    exit_code = 0
    for key in args.states:
        if args.ensembles:
            width = 178.0 if args.width_mm == 86.0 else args.width_mm
            try:
                res = process_ensemble(key, root, outdir, width, args.dpi)
            except Exception as exc:
                print(f"[{key}] ensemble FAILED: {exc}", file=sys.stderr)
                exit_code = 1
                continue
            print(f"[{key}] grid: {res.get('grid')}  n={res.get('n')}  size_px: {res.get('size_px')}")
            for e in res.get("errors", []):
                print(f"[{key}] {e}", file=sys.stderr)
                exit_code = 1
            continue
        try:
            res = process_state(key, root, outdir, args.width_mm, args.dpi)
        except Exception as exc:  # report and continue with the other states
            print(f"[{key}] FAILED: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        if "status" in res:
            print(f"[{key}] {res['status']}: {res['src']}", file=sys.stderr)
            exit_code = 1
            continue
        print(f"[{key}] files: {res['files']}  size_px: {res.get('size_px')}")
        for e in res["errors"]:
            print(f"[{key}] {e}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
