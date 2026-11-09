#!/usr/bin/env python3
"""Seven Nd_Ag + 2 V_Ag configurations of Ag2CrO4 (222 atoms), vacancies marked by ghost atoms.

Style = user's VESTA reference (Ag2CrO4/CONTCAR.eps, 2026-11-09): full structure, Ag grey, Cr navy,
O red, Nd orange, half-coloured thin bonds, dashed black cell, white background, POV-Ray finish of
`render_structures.py`. The two vacated Ag sites are sky-blue ghost atoms inside translucent
sky-blue O polyhedra (tetrahedron = Ag2/T site, octahedron = Ag1/O site) so the distortion of each
polyhedron in the relaxed cell is visible.
Ghost position = centroid of the O polyhedron of the vacated site in the relaxed complex; the site
is found by optimal assignment of the Ag atoms to the 224-atom parent cell (Supplemental Table S3).

Usage (render_env, needs povray):
    ~/.conda/envs/render_env/bin/python plot_vacancy_configs.py \
        --root ~/work_vasp/Ag2CrO4/paw_pbe_1.125xENMAX_Etot/DEFECT_MODELS/Ag_by_Nd_1_1 \
        --out ~/work_vasp/Ag2CrO4/paper/Figures/vacancy_configs
Outputs: <out>.png (600 dpi), <out>.eps (PNG inside, Flate), <out>_panels/*.pov|png, <out>.csv (sites).
"""
import argparse
import csv
import math
import os
import subprocess
import sys

import numpy as np
import ase.io
from ase.geometry import get_distances
from PIL import Image
from scipy.optimize import linear_sum_assignment
from scipy.spatial import ConvexHull, cKDTree

sys.path.insert(0, os.path.expanduser("~/.claude/skills/academic-figure-skill/scripts"))
from render_structures import png_to_eps, _srgb_to_linear  # noqa: E402

POVRAY = os.environ.get("POVRAY", os.path.expanduser("~/.conda/envs/render_env/bin/povray"))

# folder -> label (publication notation; edit here only). Order = panel order.
CONFIGS = [
    ("Ag_T_N",      r"$2V_{\mathrm{Ag,TO1}}$"),
    ("Ag_TeO_N",    r"$2V_{\mathrm{Ag,TO2}}$"),
    ("Ag_TeO_NeF",  r"$2V_{\mathrm{Ag,TO3}}$"),
    ("Ag_TeO_F",    r"$2V_{\mathrm{Ag,TO4}}$"),
    ("Ag_O_N",      r"$2V_{\mathrm{Ag,OO1}}$"),
    ("Ag_O_F",      r"$2V_{\mathrm{Ag,OO2}}$"),
    ("Ag_T_F",      r"$2V_{\mathrm{Ag,TT}}$"),
]
# colours sampled from the reference render (sphere body); ghost/polyhedra sky blue (user, 2026-11-09)
COL = {"Ag": "#C0C4C5", "Cr": "#2020A0", "O": "#F8211F", "Nd": "#F99A1F",
       "ghost": "#8FD3F4", "poly": "#6EC1EA", "edge": "#2E9FD6"}
RAD = {"Ag": 0.56, "Cr": 0.50, "O": 0.30, "Nd": 0.73, "ghost": 0.42}   # A, measured on the reference (c = 20.46 A -> ~34 px/A)
BOND_R = 0.07
FRONT_SHIFT = 80.0   # A, see build_scene.F
FACE_T = 0.60        # transparency of the polyhedron faces
BOND_MAX = {("Ag", "O"): 2.75, ("Cr", "O"): 2.0, ("Nd", "O"): 2.8}
IMG_TOL = 0.02   # fractional margin: atoms this close to a cell face are repeated on the opposite face
FIN = "finish { ambient 0.25 diffuse 0.75 specular 0.3 roughness 0.01 phong 0.9 phong_size 90 }"
TILT_V, TILT_U = 28.0, 14.0   # deg: view rotation about the vertical / horizontal screen axes


def lin(h):
    h = h.lstrip("#")
    return tuple(_srgb_to_linear(int(h[k:k + 2], 16) / 255) for k in (0, 2, 4))


def rgb(h):
    """Colour as written to POV-Ray. The PNG written by this POV-Ray build is NOT gamma-encoded here
    (measured 2026-11-09: rendered body = input value), so the sRGB hex goes in as is; the
    linearised input of render_structures.py gave dark, over-saturated spheres in this scene."""
    h = h.lstrip("#")
    return "<%.4f,%.4f,%.4f>" % tuple(int(h[k:k + 2], 16) / 255 for k in (0, 2, 4))


def mic(v, cell):
    f = np.linalg.solve(cell.T, v)
    return cell.T @ (f - np.round(f))


def _rot():
    tv, tu = math.radians(TILT_V), math.radians(TILT_U)
    ry = np.array([[math.cos(tv), 0, math.sin(tv)], [0, 1, 0], [-math.sin(tv), 0, math.cos(tv)]])
    rx = np.array([[1, 0, 0], [0, math.cos(tu), -math.sin(tu)], [0, math.sin(tu), math.cos(tu)]])
    return rx @ ry


ROT = _rot()


def to_screen(v, centre):
    """Crystal Cartesian (x,y,z) -> screen (u=z, v=y, w=x): c horizontal, b vertical, a into the page; tilted."""
    q = np.asarray(v) - centre
    return ROT @ np.array([q[2], q[1], q[0]])


# ------------------------------------------------------------------ data
def analyse(root, name, parent):
    a = ase.io.read(f"{root}/vacancies_compensation/{name}_OK/CONTCAR")
    cell = np.array(a.cell)
    s = np.array(a.get_chemical_symbols())
    ps = np.array(parent.get_chemical_symbols())
    ag = a.positions[s == "Ag"]
    ox = a.positions[s == "O"]
    pag = parent.positions[ps == "Ag"]
    pox = parent.positions[ps == "O"]
    D = get_distances(pag, ag, cell=parent.cell, pbc=True)[1]
    r, _ = linear_sum_assignment(D)
    vac = sorted(set(range(len(pag))) - set(r))
    ghosts = []
    for u in vac:
        dd = np.sort(np.linalg.norm(np.array([mic(o - pag[u], cell) for o in pox]), axis=1))
        site = "O" if dd[4] < 2.85 else "T"          # Ag1 octahedral (6 O), Ag2 tetrahedral (4 O)
        n = 6 if site == "O" else 4
        dv = np.array([mic(o - pag[u], cell) for o in ox])
        idx = np.argsort(np.linalg.norm(dv, axis=1))[:n]
        cen = pag[u] + dv[idx].mean(axis=0)
        ghosts.append(dict(pos=cen, site=site, verts=[pag[u] + dv[i] for i in idx]))
    return dict(cell=cell, atoms=a, ghosts=ghosts)


def with_images(pos, cell):
    """Wrap into the cell and repeat atoms lying on a face (VESTA boundary atoms)."""
    f = np.linalg.solve(cell.T, np.asarray(pos).T).T
    f -= np.floor(f + 1e-9)
    out = []
    for fi in f:
        sh = [[0, 1] if fi[k] < IMG_TOL else ([0, -1] if fi[k] > 1 - IMG_TOL else [0]) for k in range(3)]
        for i in sh[0]:
            for j in sh[1]:
                for k in sh[2]:
                    out.append(cell.T @ (fi + np.array([i, j, k])))
    return out


def poly_edges(pts):
    pts = np.array(pts)
    if len(pts) == 4:
        return [(i, j) for i in range(4) for j in range(i + 1, 4)], [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    h = ConvexHull(pts)
    e = set()
    for t in h.simplices:
        for i in range(3):
            e.add(tuple(sorted((int(t[i]), int(t[(i + 1) % 3])))))
    return sorted(e), [tuple(int(k) for k in t) for t in h.simplices]


# ------------------------------------------------------------------ POV
def V(p):
    return "<%.4f,%.4f,%.4f>" % tuple(p)


def sph(p, r, tx):
    return f"sphere {{ {V(p)}, {r:.4f} {tx} }}\n"


def cyl(a, b, r, tx):
    return f"cylinder {{ {V(a)}, {V(b)}, {r:.4f} {tx} }}\n"


def tex(h):
    return f"texture {{ pigment {{ rgb {rgb(h)} }} {FIN} }}"


def build_scene(d, centre, half_u, half_v):
    cell = d["cell"]
    a = d["atoms"]
    sym = np.array(a.get_chemical_symbols())
    drawn = []                                    # (element, cartesian position)
    for el in ("Ag", "Cr", "O", "Nd"):
        for p in with_images(a.positions[sym == el], cell):
            drawn.append((el, p))
    # ghosts: wrap the centre into the cell (polyhedron vertices follow)
    ghost_items = []
    for g in d["ghosts"]:
        f = np.linalg.solve(cell.T, g["pos"])
        sh = cell.T @ (-np.floor(f))
        c0 = g["pos"] + sh
        verts = [v + sh for v in g["verts"]]
        ghost_items.append((c0, verts))     # no periodic image: exactly two ghosts per panel, polyhedron kept whole
    # polyhedron vertices with no O sphere drawn there (image beyond the tolerance): add it
    tree = cKDTree(np.array([p for el, p in drawn if el == "O"]))
    for c, verts in ghost_items:
        for v in verts:
            if tree.query(v)[0] > 0.3:
                drawn.append(("O", v))
    S = lambda p: to_screen(p, centre)
    s = ""
    for el, p in drawn:
        s += sph(S(p), RAD[el], tex(COL[el]))
    pos = np.array([p for el, p in drawn])
    els = [el for el, p in drawn]
    for i, j in sorted(cKDTree(pos).query_pairs(2.85)):
        pair = tuple(sorted((els[i], els[j])))
        if pair not in BOND_MAX or np.linalg.norm(pos[i] - pos[j]) > BOND_MAX[pair]:
            continue
        mid = (pos[i] + pos[j]) / 2
        s += cyl(S(pos[i]), S(mid), BOND_R, tex(COL[els[i]]))
        s += cyl(S(pos[j]), S(mid), BOND_R, tex(COL[els[j]]))
    pc = tuple(int(COL["poly"].lstrip("#")[k:k + 2], 16) / 255 for k in (0, 2, 4))
    cam = 1000.0

    def F(p):
        """Screen position moved FRONT_SHIFT A towards the camera with the lateral part rescaled so the
        projection is unchanged: polyhedra/ghosts are drawn on top of the atoms in front of them."""
        q = S(p)
        k = (cam + q[2] - FRONT_SHIFT) / (cam + q[2])
        return np.array([q[0] * k, q[1] * k, q[2] - FRONT_SHIFT]), k

    for c, verts in ghost_items:
        pts = np.array(verts)
        edges, faces = poly_edges(pts)
        fp = [F(x) for x in pts]
        for i, j in edges:
            s += cyl(fp[i][0], fp[j][0], 0.055 * fp[i][1],
                     f"texture {{ pigment {{ rgb {rgb(COL['edge'])} }} finish {{ ambient 0.8 diffuse 0.3 }} }}")
        for f in faces:
            q = [fp[k][0] for k in f]
            s += (f"triangle {{ {V(q[0])}, {V(q[1])}, {V(q[2])} pigment {{ rgbt <{pc[0]:.3f},{pc[1]:.3f},{pc[2]:.3f},{FACE_T}> }} "
                  f"finish {{ ambient 0.8 diffuse 0.2 }} }}\n")
        g, k = F(c)
        s += sph(g, RAD["ghost"] * k, tex(COL["ghost"]))
    # dashed cell
    corners = {(i, j, k): i * cell[0] + j * cell[1] + k * cell[2] for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    dash = "texture { pigment { rgb <0,0,0> } finish { ambient 1 diffuse 0 } }"
    for k1, p1 in corners.items():
        for k2, p2 in corners.items():
            if k1 < k2 and sum(abs(x - y) for x, y in zip(k1, k2)) == 1:
                n = int(np.linalg.norm(p2 - p1) / 0.7)
                for m in range(0, n, 2):
                    s += cyl(S(p1 + (p2 - p1) * m / n), S(p1 + (p2 - p1) * min(m + 1, n) / n), 0.03, dash)
    head = ["background { color rgb <1,1,1> }", "camera {", "  location <0,0,-1000>", "  look_at <0,0,0>",
            f"  angle {math.degrees(2 * math.atan(half_u / 1000)):.6f}",
            f"  right <{2 * half_u:.5f},0,0>", f"  up <0,{2 * half_v:.5f},0>", "}",
            "light_source { <-250,250,-500> color rgb <1,1,1> shadowless }",
            "light_source { <300,-150,-400> color rgb <0.25,0.25,0.25> shadowless }"]
    return "\n".join(head) + "\n" + s


def render(pov, png, wpx, hpx):
    cmd = [POVRAY, f"+I{pov}", f"+O{png}", f"+W{wpx}", f"+H{hpx}", "+A0.1", "+UA", "-D"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode != 0 or not os.path.exists(png):
        raise RuntimeError(r.stderr[-600:])
    im = Image.open(png)
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        bg.save(png)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="Ag_by_Nd_1_1 folder (parent 224-atom CONTCAR + vacancies_compensation/)")
    ap.add_argument("--out", required=True, help="output prefix")
    ap.add_argument("--width-mm", type=float, default=178.0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--ncol", type=int, default=3)
    ap.add_argument("--only", help="comma list of folder names (test)")
    a = ap.parse_args()

    parent = ase.io.read(f"{a.root}/CONTCAR")
    pdir = a.out + "_panels"
    os.makedirs(pdir, exist_ok=True)
    cell = np.array(parent.cell)
    centre = cell.sum(axis=0) / 2
    cor = np.array([to_screen(i * cell[0] + j * cell[1] + k * cell[2], centre)
                    for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    half_u = np.abs(cor[:, 0]).max() + 1.2
    half_v = np.abs(cor[:, 1]).max() + 1.2
    ncol = a.ncol
    cwpx = int(round(a.width_mm / ncol / 25.4 * a.dpi))
    chpx = int(round(cwpx * half_v / half_u))
    sel = CONFIGS if not a.only else [c for c in CONFIGS if c[0] in a.only.split(",")]
    nrow = math.ceil((len(sel) + 1) / ncol)
    ind = parent.get_chemical_symbols().index("Nd")
    rows = []
    for name, lab in sel:
        d = analyse(a.root, name, parent)
        pov, png = f"{pdir}/{name}.pov", f"{pdir}/{name}.png"
        open(pov, "w").write(build_scene(d, centre, half_u, half_v))
        render(pov, png, cwpx, chpx)
        dn = [np.linalg.norm(mic(g["pos"] - parent.positions[ind], cell)) for g in d["ghosts"]]
        rows.append([name, lab, "+".join(g["site"] for g in d["ghosts"]), *["%.2f" % x for x in dn]])
        print(name, [g["site"] for g in d["ghosts"]], ["%.2f" % x for x in dn])
    with open(a.out + ".csv", "w", newline="") as fh:
        csv.writer(fh).writerows([["folder", "label", "sites", "d_Nd-ghost_1_A", "d_Nd-ghost_2_A"], *rows])
    compose(sel, pdir, a, cwpx, chpx, ncol, nrow)


def compose(sel, pdir, a, cwpx, chpx, ncol, nrow):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "STIXGeneral"],
                     "mathtext.fontset": "stix", "ps.fonttype": 42, "pdf.fonttype": 42, "font.size": 10})
    wmm = a.width_mm
    hmm = wmm / ncol * chpx / cwpx * nrow
    fig = plt.figure(figsize=(wmm / 25.4, hmm / 25.4), dpi=a.dpi)
    box = dict(fc="white", ec="none", pad=1.0)
    letters = "abcdefgh"

    def axes_at(k):
        r_, c_ = divmod(k, ncol)
        return fig.add_axes([c_ / ncol, 1 - (r_ + 1) / nrow, 1 / ncol, 1 / nrow])

    for k, (name, lab) in enumerate(sel):
        ax = axes_at(k)
        ax.imshow(np.asarray(Image.open(f"{pdir}/{name}.png").convert("RGB")), interpolation="none", aspect="auto")
        ax.axis("off")
        ax.text(0.01, 0.99, f"{letters[k]})", transform=ax.transAxes, fontweight="bold", ha="left", va="top", bbox=box)
        ax.text(0.99, 0.99, lab, transform=ax.transAxes, ha="right", va="top", bbox=box)
    k = len(sel)
    if k < ncol * nrow:                                   # key panel
        ax = axes_at(k)
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        items = [(COL["Ag"], "Ag"), (COL["Cr"], "Cr"), (COL["O"], "O"), (COL["Nd"], "Nd"),
                 (COL["ghost"], r"$V_{\mathrm{Ag}}$ (ghost atom)")]
        for i, (c, t) in enumerate(items):
            y = 0.86 - 0.12 * i
            ax.scatter([0.06], [y], s=70, c=c, edgecolors="k", linewidths=0.4, zorder=3)
            ax.text(0.11, y, t, va="center", ha="left")
        ax.add_patch(plt.Rectangle((0.03, 0.20), 0.06, 0.07, fc=COL["poly"], ec=COL["poly"], alpha=0.5, lw=1.0))
        ax.text(0.11, 0.235, "O polyhedron of the vacated site", va="center", ha="left")
        ax.text(0.03, 0.08, "T: tetrahedron (Ag2), O: octahedron (Ag1)", va="center", ha="left")
        ax.text(0.01, 0.99, f"{letters[k]})", fontweight="bold", va="top", ha="left", bbox=box)
    png = a.out + ".png"
    fig.savefig(png, dpi=a.dpi)
    try:
        png_to_eps(png, a.out + ".eps", wmm)
    except FileNotFoundError:   # gs (validator) not on PATH; EPS is written before validation
        print("WARNING: gs not found, EPS not validated")
    print("wrote", png, a.out + ".eps")


if __name__ == "__main__":
    main()
