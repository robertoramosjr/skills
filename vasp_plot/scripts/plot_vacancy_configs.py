#!/usr/bin/env python3
"""Seven Nd_Ag + 2 V_Ag configurations of Ag2CrO4 (222 atoms), vacancies marked by ghost atoms.

Each panel: relaxed CONTCAR of one complex, Nd-centred periodic box viewed along a, Ag as small
spheres, Nd large, the two vacated Ag sites as translucent ghost spheres inside their O
coordination polyhedra (tetrahedron = Ag2/T, octahedron = Ag1/O), Nd inside its own O octahedron.
CrO4 units are not drawn (clutter). Ghost positions = centroid of the O polyhedron of the vacated
site in the relaxed complex (site found by optimal assignment of the Ag atoms to the 224-atom
parent cell, as in Supplemental Table S3).

Usage (render_env, needs povray):
    ~/.conda/envs/render_env/bin/python plot_vacancy_configs.py \
        --root ~/work_vasp/Ag2CrO4/paw_pbe_1.125xENMAX_Etot/DEFECT_MODELS/Ag_by_Nd_1_1 \
        --out ~/work_vasp/Ag2CrO4/paper/Figures/vacancy_configs
Outputs: <out>.png (600 dpi), <out>.eps (PNG inside, Flate), <out>_panels/*.pov, <out>.csv (sites).
"""
import argparse
import math
import os
import subprocess
import sys

import numpy as np
import ase.io
from PIL import Image
from scipy.optimize import linear_sum_assignment
from scipy.spatial import ConvexHull

sys.path.insert(0, os.path.expanduser("~/.claude/skills/academic-figure-skill/scripts"))
from render_structures import png_to_eps, _srgb_to_linear  # noqa: E402

POVRAY = os.environ.get("POVRAY", os.path.expanduser("~/.conda/envs/render_env/bin/povray"))

# folder -> (label shown, LaTeX name). Labels are a proposal; edit here only.
CONFIGS = [
    ("Ag_T_N",      r"$2V_{\mathrm{Ag,TO1}}$"),
    ("Ag_TeO_N",    r"$2V_{\mathrm{Ag,TO2}}$"),
    ("Ag_TeO_NeF",  r"$2V_{\mathrm{Ag,TO3}}$"),
    ("Ag_TeO_F",    r"$2V_{\mathrm{Ag,TO4}}$"),
    ("Ag_O_N",      r"$2V_{\mathrm{Ag,OO1}}$"),
    ("Ag_O_F",      r"$2V_{\mathrm{Ag,OO2}}$"),
    ("Ag_T_F",      r"$2V_{\mathrm{Ag,TT}}$"),
]
COL = {"Ag": "#D55E00", "Cr": "#0072B2", "O": "#009E73", "Nd": "#CC79A7"}
R = {"Ag": 0.42, "Nd": 1.15, "O": 0.30, "ghost": 0.95}
FIN = "finish { ambient 0.25 diffuse 0.75 specular 0.3 roughness 0.01 phong 0.9 phong_size 90 }"


def lin(h):
    h = h.lstrip("#")
    return tuple(_srgb_to_linear(int(h[k:k + 2], 16) / 255) for k in (0, 2, 4))


def rgb(h):
    return "<%.4f,%.4f,%.4f>" % lin(h)


def mic(v, cell):
    f = np.linalg.solve(cell.T, v)
    return cell.T @ (f - np.round(f))


def analyse(root, name, parent):
    """Return dict with Nd position (0), Ag positions, ghosts [(pos, site, O positions)]."""
    a = ase.io.read(f"{root}/vacancies_compensation/{name}_OK/CONTCAR")
    cell = np.array(a.cell)
    s = np.array(a.get_chemical_symbols())
    ps = np.array(parent.get_chemical_symbols())
    nd = a.positions[s == "Nd"][0]
    ag = a.positions[s == "Ag"]
    ox = a.positions[s == "O"]
    pag = parent.positions[ps == "Ag"]
    pnd = parent.positions[ps == "Nd"][0]
    from ase.geometry import get_distances
    D = get_distances(pag, ag, cell=parent.cell, pbc=True)[1]
    r, _ = linear_sum_assignment(D)
    vac = sorted(set(range(len(pag))) - set(r))
    # neighbour counts in the parent: Ag1 octahedral (6 O), Ag2 tetrahedral (4 O)
    pox = parent.positions[ps == "O"]
    out = []
    for u in vac:
        dv = np.array([mic(o - pag[u], cell) for o in pox])
        dd = np.linalg.norm(dv, axis=1)
        order = np.argsort(dd)
        site = "O" if dd[order[5]] < 3.15 and dd[order[4]] < 3.0 and dd[order[3]] < 2.7 else "T"
        # robust: Ag1 has 6 O below 3.15 A with the 5th < 2.8; Ag2 has a 5th O above 2.9
        site = "O" if dd[order[4]] < 2.85 else "T"
        n = 6 if site == "O" else 4
        # same sites in the relaxed complex: nearest n O to the parent position
        dv2 = np.array([mic(o - pag[u], cell) for o in ox])
        o_idx = np.argsort(np.linalg.norm(dv2, axis=1))[:n]
        cen = pag[u] + dv2[o_idx].mean(axis=0)
        out.append((cen, site, [cen + (dv2[i] - dv2[o_idx].mean(axis=0)) for i in o_idx]))
    # Nd octahedron
    dn = np.array([mic(o - nd, cell) for o in ox])
    n_idx = np.argsort(np.linalg.norm(dn, axis=1))[:6]
    nd_o = [nd + dn[i] for i in n_idx]
    return dict(cell=cell, nd=nd, ag=ag, ghosts=out, nd_o=nd_o,
                ag_vec=np.array([mic(p - nd, cell) for p in ag]))


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


def sph(p, r, tex):
    return f"sphere {{ <{p[0]:.4f},{p[1]:.4f},{p[2]:.4f}>, {r} {tex} }}\n"


def cyl(a, b, r, tex):
    return (f"cylinder {{ <{a[0]:.4f},{a[1]:.4f},{a[2]:.4f}>, <{b[0]:.4f},{b[1]:.4f},{b[2]:.4f}>, {r} {tex} }}\n")


TILT_V = 18.0   # deg about the screen-vertical axis (separates atoms stacked along a)
TILT_U = 10.0   # deg about the screen-horizontal axis


def _rot():
    tv, tu = math.radians(TILT_V), math.radians(TILT_U)
    ry = np.array([[math.cos(tv), 0, math.sin(tv)], [0, 1, 0], [-math.sin(tv), 0, math.cos(tv)]])
    rx = np.array([[1, 0, 0], [0, math.cos(tu), -math.sin(tu)], [0, math.sin(tu), math.cos(tu)]])
    return rx @ ry


ROT = _rot()


def to_screen(v):
    """Crystal Cartesian (x,y,z) -> POV screen (u=z, v=y, w=x) (look down a, c horizontal), then tilted."""
    return ROT @ np.array([v[2], v[1], v[0]])


def poly_pov(cen, pts, col, edge_r=0.045, face_tr=0.80):
    pts_s = [to_screen(p) for p in pts]
    edges, faces = poly_edges(np.array(pts))
    s = ""
    for i, j in edges:
        s += cyl(pts_s[i], pts_s[j], edge_r, f"texture {{ pigment {{ rgb {rgb(col)} }} finish {{ ambient 0.5 diffuse 0.5 }} }}")
    for f in faces:
        a, b, c = (pts_s[k] for k in f)
        t = lambda p: f"<{p[0]:.4f},{p[1]:.4f},{p[2]:.4f}>"
        s += (f"triangle {{ {t(a)}, {t(b)}, {t(c)} pigment {{ rgbt <{lin(col)[0]:.3f},{lin(col)[1]:.3f},"
              f"{lin(col)[2]:.3f},{face_tr}> }} finish {{ ambient 0.6 diffuse 0.3 }} }}\n")
    return s


def write_panel(d, path, wpx, hpx, half_u, half_v):
    # box centred on the Nd + 2 ghosts cluster (MIC), so far vacancies are not cut by the cell edge
    gv = [mic(g[0] - d["nd"], d["cell"]) for g in d["ghosts"]]
    sh = (np.zeros(3) + gv[0] + gv[1]) / 3.0
    d = dict(d)
    d["ag_vec"] = np.array([mic(v - sh, d["cell"]) for v in d["ag_vec"]])
    d["sh"] = sh
    nd_s = -sh
    lines = ['background { color rgb <1,1,1> }',
             "camera {", f"  location <0,0,-1000>", "  look_at <0,0,0>",
             f"  angle {math.degrees(2 * math.atan(half_u / 1000)):.6f}",
             f"  right <{2 * half_u:.5f},0,0>", f"  up <0,{2 * half_v:.5f},0>", "}",
             "light_source { <-30,30,-60> color rgb <1,1,1> }",
             "light_source { <40,-20,-40> color rgb <0.25,0.25,0.25> shadowless }"]
    s = "\n".join(lines) + "\n"
    pale = tuple(0.45 * c + 0.55 for c in lin(COL["Ag"]))
    ag_col = f"texture {{ pigment {{ rgbt <{pale[0]:.3f},{pale[1]:.3f},{pale[2]:.3f},0.15> }} {FIN} }}"
    for v in d["ag_vec"]:
        s += sph(to_screen(v), R["Ag"], ag_col)
    # unit cell box
    cell = d["cell"]
    corners = []
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                corners.append(i * cell[0] + j * cell[1] + k * cell[2] - 0.5 * cell.sum(axis=0))
    for ia in range(8):
        for ib in range(ia + 1, 8):
            if bin(ia ^ ib).count("1") == 1:
                s += cyl(to_screen(corners[ia]), to_screen(corners[ib]), 0.03,
                         "texture { pigment { rgb <0.35,0.35,0.35> } finish { ambient 1 } }")
    # Nd and its octahedron
    s += poly_pov(nd_s, [p - d["nd"] - sh for p in d["nd_o"]], COL["Nd"], face_tr=0.80)
    s += sph(to_screen(nd_s), R["Nd"], f"texture {{ pigment {{ rgb {rgb(COL['Nd'])} }} {FIN} }}")
    # ghosts
    for cen, site, opos in d["ghosts"]:
        c = mic(cen - d["nd"], d["cell"]) - sh
        pts = [c + (o - cen) for o in opos]
        s += poly_pov(c, pts, "#555555", face_tr=0.93)
        for p in pts:
            s += sph(to_screen(p), R["O"], f"texture {{ pigment {{ rgb {rgb(COL['O'])} }} {FIN} }}")
        s += sph(to_screen(c), R["ghost"],
                 "texture { pigment { rgbt <1,1,1,0.35> } finish { ambient 0.4 diffuse 0.4 specular 0.5 phong 0.6 phong_size 60 } }")
    with open(path, "w") as fh:
        fh.write(s)


def render(pov, png, wpx, hpx):
    cmd = [POVRAY, f"+I{pov}", f"+O{png}", f"+W{wpx}", f"+H{hpx}", "+A0.1", "+UA", "-D"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not os.path.exists(png):
        raise RuntimeError(r.stderr[-600:])
    im = Image.open(png)
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        bg.save(png)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="Ag_by_Nd_1_1 folder (parent 224-atom CONTCAR + vacancies_compensation/)")
    ap.add_argument("--out", required=True, help="output prefix")
    ap.add_argument("--width-mm", type=float, default=178.0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--only", help="comma list of folder names (test)")
    a = ap.parse_args()

    parent = ase.io.read(f"{a.root}/CONTCAR")
    pdir = a.out + "_panels"
    os.makedirs(pdir, exist_ok=True)
    ncol, nrow = 4, 2
    cw = a.width_mm / ncol
    cwpx = int(round(cw / 25.4 * a.dpi))
    cell = np.array(parent.cell)
    cor = np.array([to_screen(i * cell[0] + j * cell[1] + k * cell[2] - 0.5 * cell.sum(axis=0))
                    for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    half_u = np.abs(cor[:, 0]).max() + 1.9   # margin: far vacancies (10-14 A) straddle the cell edge
    half_v = np.abs(cor[:, 1]).max() + 1.9
    chpx = int(round(cwpx * half_v / half_u))
    rows = []
    import csv
    sel = CONFIGS if not a.only else [c for c in CONFIGS if c[0] in a.only.split(",")]
    for name, lab in sel:
        d = analyse(a.root, name, parent)
        pov = f"{pdir}/{name}.pov"
        png = f"{pdir}/{name}.png"
        write_panel(d, pov, cwpx, chpx, half_u, half_v)
        render(pov, png, cwpx, chpx)
        dn = [np.linalg.norm(mic(g[0] - d["nd"], d["cell"])) for g in d["ghosts"]]
        rows.append([name, lab, "+".join(g[1] for g in d["ghosts"]), *["%.2f" % x for x in dn]])
        print(name, [g[1] for g in d["ghosts"]], ["%.2f" % x for x in dn])
    with open(a.out + ".csv", "w", newline="") as fh:
        csv.writer(fh).writerows([["folder", "label", "sites", "d_Nd-V_ghost_1_A", "d_Nd-V_ghost_2_A"], *rows])
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
    letters = "abcdefgh"
    for k, (name, lab) in enumerate(sel):
        r_, c_ = divmod(k, ncol)
        ax = fig.add_axes([c_ / ncol, 1 - (r_ + 1) / nrow, 1 / ncol, 1 / nrow])
        ax.imshow(np.asarray(Image.open(f"{pdir}/{name}.png").convert("RGB")), interpolation="none", aspect="auto")
        ax.axis("off")
        ax.text(0.02, 0.97, f"{letters[k]})", transform=ax.transAxes, fontweight="bold", ha="left", va="top",
                bbox=dict(fc="white", ec="none", pad=1.0))
        ax.text(0.98, 0.97, lab, transform=ax.transAxes, ha="right", va="top",
                bbox=dict(fc="white", ec="none", pad=1.0))
    if len(sel) < ncol * nrow:
        k = len(sel)
        r_, c_ = divmod(k, ncol)
        ax = fig.add_axes([c_ / ncol, 1 - (r_ + 1) / nrow, 1 / ncol, 1 / nrow])
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        items = [("#CC79A7", "Nd"), ("#E8B49A", "Ag"), ("#009E73", "O (polyhedra)"),
                 ("#F2F2F2", "$V_{\\mathrm{Ag}}$ (ghost atom)")]
        for i, (c, t) in enumerate(items):
            y = 0.80 - 0.20 * i
            ax.scatter([0.08], [y], s=60, c=c, edgecolors="k", linewidths=0.5, zorder=3)
            ax.text(0.16, y, t, va="center", ha="left", fontsize=10)
        ax.text(0.02, 0.97, "h)", fontweight="bold", va="top", ha="left", bbox=dict(fc="white", ec="none", pad=1.0))
    png = a.out + ".png"
    fig.savefig(png, dpi=a.dpi)
    try:
        png_to_eps(png, a.out + ".eps", wmm)
    except FileNotFoundError:   # gs (validator) not on PATH; EPS is written before validation
        print("WARNING: gs not found, EPS not validated")
    print("wrote", png, a.out + ".eps")


if __name__ == "__main__":
    main()
