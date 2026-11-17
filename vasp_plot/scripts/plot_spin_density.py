#!/usr/bin/env python3
"""Spin-density isosurfaces (rho_up - rho_down) around a dopant, one panel per structure, same window.

Literature convention for spin densities of doped oxides (VESTA-style): two colours, yellow = positive
(majority spin of the dopant), cyan = negative, ONE isovalue in e/A^3 for all panels, stated in the
caption; panels share the view and the window, centred on the dopant.
Project style = Fig. 1 of paper 2 (`vasp_plot/scripts/plot_vacancy_configs.py`): same element colours
(Ag grey, Cr navy, O red, Nd orange), radii, half-coloured bonds, shiny POV-Ray finish, view
(c horizontal, b vertical, a into the page, tilted) and sky-blue ghost atoms on the vacated Ag sites.

Data: CHGCAR_SPIN (single volumetric block, VASP convention rho*V_cell), or else the magnetization (2nd) block
of CHGCAR, + CONTCAR of the same folder.
The sign of each panel is chosen so that the moment of the dopant is positive (VASP may converge to
M < 0); say so in the caption. The isosurface is drawn by POV-Ray from a df3 density file cropped to
the display box (no marching cubes needed); atoms are shown inside the same Cartesian box around the
dopant (|dx|, |dy|, |dz| <= HALF), so the slab is identical in all panels.

Usage (render_env):
    ~/.conda/envs/render_env/bin/python plot_spin_density.py \
        --panel DIR:LABEL[:GHOSTS] [...] --iso 0.01 --out ~/work_vasp/Ag2CrO4/paper/Figures/spin_density
  GHOSTS = folder name of the vacancy configuration as in plot_vacancy_configs (e.g. Ag_T_N), whose
  vacated sites are found against --parent (224-atom CONTCAR).
"""
import argparse
import math
import os
import struct
import subprocess
import sys

import numpy as np
import ase.io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plot_vacancy_configs as pvc  # noqa: E402  (COL, RAD, FIN, ROT, bonds, render, png_to_eps)

HALF = np.array([3.0, 6.2, 8.6])          # A, half box along x(a), y(b), z(c) around the dopant
ISO_COL = {"+": "#F2D21B", "-": "#22B8D8"}  # yellow / cyan (VESTA convention)
ISO_T = 0.50                               # transmit of the isosurfaces
CAP = 10.0                                 # values clipped at CAP*iso before normalising (bounded gradient)


def read_vol(path, block=1):
    """Volumetric block `block` (1 = first; CHGCAR of ISPIN=2: 1 = total, 2 = magnetization), rho*V."""
    with open(path) as f:
        lines = f.readlines()
    nat = sum(int(x) for x in lines[6].split())
    i = 8 + nat
    while not lines[i].split():
        i += 1
    gline = lines[i].split()
    ng = tuple(int(x) for x in gline)
    n = int(np.prod(ng))
    for b in range(block):
        if b > 0:
            i = j
            while lines[i].split() != gline:
                i += 1
        vals, j = [], i + 1
        while len(vals) < n:
            vals.extend(lines[j].split())
            j += 1
    return np.array(vals[:n], float).reshape(ng[::-1]).transpose(2, 1, 0)   # [ix, iy, iz]


def write_df3(path, arr):
    """df3: 3 big-endian uint16 dims, then 16-bit big-endian data, x fastest."""
    a = np.clip(np.round(arr * 65535), 0, 65535).astype(">u2")
    with open(path, "wb") as f:
        f.write(struct.pack(">HHH", *arr.shape))
        f.write(a.transpose(2, 1, 0).tobytes())


def prepare(folder, centre_el, parent, ghosts_name, root):
    at = ase.io.read(os.path.join(folder, "CONTCAR"))
    cell = np.array(at.cell)
    L = np.diag(cell)
    if np.abs(cell - np.diag(L)).max() > 1e-6:
        raise SystemExit("orthorhombic cell expected")
    spin = os.path.join(folder, "CHGCAR_SPIN")
    rho = (read_vol(spin) if os.path.exists(spin) else read_vol(os.path.join(folder, "CHGCAR"), block=2)) / at.get_volume()
    sym = np.array(at.get_chemical_symbols())
    ic = int(np.where(sym == centre_el)[0][0])
    f0 = at.get_scaled_positions()[ic]
    g0 = rho.reshape(-1)[np.ravel_multi_index(tuple(np.round(f0 * rho.shape).astype(int) % rho.shape), rho.shape)]
    sign = 1.0 if g0 > 0 else -1.0
    rho *= sign
    p0 = at.positions[ic]
    # atoms (with periodic images) inside the box
    items = []
    for s, p in zip(sym, at.positions):
        d = p - p0
        d -= L * np.round(d / L)
        for sh in np.array(np.meshgrid([-1, 0, 1], [-1, 0, 1], [-1, 0, 1])).T.reshape(-1, 3):
            q = d + sh * L
            if np.all(np.abs(q) <= HALF + 0.05):
                items.append((s, q))
    ghosts = []
    if ghosts_name:
        dd = pvc.analyse(root, ghosts_name, parent)
        for g in dd["ghosts"]:
            q = g["pos"] - p0
            q -= L * np.round(q / L)
            ghosts.append(q)
    # grid cropped to the box (periodic), coordinates relative to the dopant
    sub, lo, hi = [], [], []
    idx = []
    for k in range(3):
        n = rho.shape[k]
        i0 = int(math.floor((f0[k] - HALF[k] / L[k]) * n)) - 1
        i1 = int(math.ceil((f0[k] + HALF[k] / L[k]) * n)) + 1
        idx.append(np.arange(i0, i1 + 1) % n)
        lo.append(i0 / n * L[k] - p0[k])
        hi.append(i1 / n * L[k] - p0[k])
    sub = rho[np.ix_(*idx)]
    return dict(items=items, ghosts=ghosts, sub=sub, lo=np.array(lo), hi=np.array(hi), sign=sign,
                M=float(rho.sum() * at.get_volume() / rho.size), atoms=at)


def scene(d, iso, tag, pdir, half_u, half_v):
    S = lambda q: pvc.to_screen(q, np.zeros(3))
    s = ""
    pos = np.array([q for _, q in d["items"]])
    els = [e for e, _ in d["items"]]
    for e, q in d["items"]:
        s += pvc.sph(S(q), pvc.RAD[e], pvc.tex(pvc.COL[e]))
    from scipy.spatial import cKDTree
    for i, j in sorted(cKDTree(pos).query_pairs(2.85)):
        pair = tuple(sorted((els[i], els[j])))
        if pair not in pvc.BOND_MAX or np.linalg.norm(pos[i] - pos[j]) > pvc.BOND_MAX[pair]:
            continue
        mid = (pos[i] + pos[j]) / 2
        s += pvc.cyl(S(pos[i]), S(mid), pvc.BOND_R, pvc.tex(pvc.COL[els[i]]))
        s += pvc.cyl(S(pos[j]), S(mid), pvc.BOND_R, pvc.tex(pvc.COL[els[j]]))
    for g in d["ghosts"]:
        s += pvc.sph(S(g), pvc.RAD["ghost"], pvc.tex(pvc.COL["ghost"]))
    # isosurfaces: unit cube -> box [lo,hi] (crystal xyz) -> screen (u=z, v=y, w=x, then ROT)
    P = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], float)
    M = pvc.ROT @ P
    m = M.T          # POV row-vector convention
    mat = "matrix <" + ",".join("%.6f" % x for x in (*m[0], *m[1], *m[2], 0, 0, 0)) + ">"
    ext = d["hi"] - d["lo"]
    for sgn in ("+", "-"):
        arr = np.clip((d["sub"] if sgn == "+" else -d["sub"]) / (CAP * iso), 0, 1)
        if arr.max() < 1.0 / CAP:
            continue
        df3 = os.path.join(pdir, f"{tag}_{'pos' if sgn == '+' else 'neg'}.df3")
        write_df3(df3, arr)
        c = tuple(int(ISO_COL[sgn][k:k + 2], 16) / 255 for k in (1, 3, 5))
        s += (f'#declare F{tag}{"P" if sgn == "+" else "N"} = function {{ pattern {{ density_file df3 "{df3}" interpolate 1 }} }}\n'
              f'isosurface {{ function {{ {1.0 / CAP:.6f} - F{tag}{"P" if sgn == "+" else "N"}(x,y,z) }} threshold 0\n'
              f'  contained_by {{ box {{ <0.001,0.001,0.001>, <0.999,0.999,0.999> }} }} max_gradient 60 accuracy 0.0005\n'
              f'  texture {{ pigment {{ rgbt <{c[0]:.3f},{c[1]:.3f},{c[2]:.3f},{ISO_T}> }} '
              f'finish {{ ambient 0.35 diffuse 0.65 specular 0.4 roughness 0.02 }} }}\n'
              f'  no_shadow scale <{ext[0]:.5f},{ext[1]:.5f},{ext[2]:.5f}> translate <{d["lo"][0]:.5f},{d["lo"][1]:.5f},{d["lo"][2]:.5f}> {mat} }}\n')
    head = ["background { color rgb <1,1,1> }",
            "camera {", "  location <0,0,-1000>", "  look_at <0,0,0>",
            f"  angle {math.degrees(2 * math.atan(half_u / 1000)):.6f}",
            f"  right <{2 * half_u:.5f},0,0>", f"  up <0,{2 * half_v:.5f},0>", "}",
            "light_source { <-250,250,-500> color rgb <1,1,1> }",
            "light_source { <300,-150,-400> color rgb <0.25,0.25,0.25> }"]
    return "\n".join(head) + "\n" + s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel", action="append", required=True, help="DIR:LABEL[:GHOSTS]")
    ap.add_argument("--parent", help="224-atom parent folder (Ag_by_Nd_1_1) for ghost sites")
    ap.add_argument("--iso", type=float, default=0.01, help="isovalue, e/A^3")
    ap.add_argument("--centre", default="Nd")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width-mm", type=float, default=178.0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--ncol", type=int, default=0, help="panels per row (0 = all in one row)")
    a = ap.parse_args()
    parent = ase.io.read(os.path.join(a.parent, "CONTCAR")) if a.parent else None
    pdir = a.out + "_panels"
    os.makedirs(pdir, exist_ok=True)
    cor = np.array([pvc.to_screen(np.array([i, j, k]) * HALF, np.zeros(3))
                    for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)])
    half_u = np.abs(cor[:, 0]).max() * 0.80
    half_v = np.abs(cor[:, 1]).max() * 0.80
    n = len(a.panel)
    ncol = a.ncol or n
    cwpx = int(round(a.width_mm / ncol / 25.4 * a.dpi))
    chpx = int(round(cwpx * half_v / half_u))
    labels = []
    for k, spec in enumerate(a.panel):
        parts = spec.split(":")
        folder, lab = parts[0], parts[1]
        gh = parts[2] if len(parts) > 2 else None
        d = prepare(folder, a.centre, parent, gh, a.parent)
        print(f"{folder}: sign {d['sign']:+.0f}, M = {d['M']:+.2f} muB, atoms in box {len(d['items'])}, ghosts {len(d['ghosts'])}")
        tag = f"p{k}"
        pov, png = f"{pdir}/{tag}.pov", f"{pdir}/{tag}.png"
        open(pov, "w").write(scene(d, a.iso, tag, pdir, half_u, half_v))
        pvc.render(pov, png, cwpx, chpx)
        labels.append((png, lab, d["M"]))
    compose(labels, a, cwpx, chpx)


def compose(labels, a, cwpx, chpx):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    from PIL import Image
    rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "STIXGeneral"],
                     "mathtext.fontset": "stix", "ps.fonttype": 42, "pdf.fonttype": 42, "font.size": 10})
    n = len(labels)
    ncol = a.ncol or n
    nrow = math.ceil(n / ncol)
    wmm = a.width_mm
    hpan = wmm / ncol * chpx / cwpx
    key_mm = 9.0
    hmm = hpan * nrow + key_mm
    fig = plt.figure(figsize=(wmm / 25.4, hmm / 25.4), dpi=a.dpi)
    box = dict(fc="white", ec="none", pad=1.0)
    for k, (png, lab, M) in enumerate(labels):
        r_, c_ = divmod(k, ncol)
        ax = fig.add_axes([c_ / ncol, (key_mm + (nrow - 1 - r_) * hpan) / hmm, 1 / ncol, hpan / hmm])
        ax.imshow(np.asarray(Image.open(png).convert("RGB")), interpolation="none", aspect="auto")
        ax.axis("off")
        ax.text(0.015, 0.985, f"{'abcdef'[k]})", transform=ax.transAxes, fontweight="bold", ha="left", va="top", bbox=box)
        ax.text(0.985, 0.985, lab, transform=ax.transAxes, ha="right", va="top", bbox=box)
        ax.text(0.985, 0.015, rf"$M = {abs(M):.0f}\,\mu_B$", transform=ax.transAxes, ha="right", va="bottom", bbox=box)
    ax = fig.add_axes([0, 0, 1, key_mm / hmm])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    items = [(pvc.COL["Ag"], "Ag", "o"), (pvc.COL["Cr"], "Cr", "o"), (pvc.COL["O"], "O", "o"), (pvc.COL["Nd"], "Nd", "o"),
             (pvc.COL["ghost"], r"$V_{\mathrm{Ag}}$", "o"),
             (ISO_COL["+"], r"$\rho_\uparrow-\rho_\downarrow>0$", "s"), (ISO_COL["-"], r"$\rho_\uparrow-\rho_\downarrow<0$", "s")]
    xs = [0.03, 0.095, 0.16, 0.215, 0.28, 0.375, 0.565]
    for x, (c, t, mk) in zip(xs, items):
        ax.scatter([x], [0.5], s=60, c=c, marker=mk, edgecolors="k", linewidths=0.4)
        ax.text(x + 0.015, 0.5, t, va="center", ha="left")
    ax.text(0.765, 0.5, rf"isovalue $\pm{a.iso:g}$ e/\AA$^3$".replace(r"\AA", "Å"), va="center", ha="left")
    png = a.out + ".png"
    fig.savefig(png, dpi=a.dpi)
    try:
        pvc.png_to_eps(png, a.out + ".eps", wmm)
    except FileNotFoundError:
        print("WARNING: gs not found, EPS not validated")
    print("wrote", png, a.out + ".eps")


if __name__ == "__main__":
    main()
