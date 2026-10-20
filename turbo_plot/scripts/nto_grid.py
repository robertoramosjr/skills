#!/usr/bin/env python3
"""Grid of NTO renders (hole | electron of NTO pair 1), one row per (state, root), common scale in every cell.

Rows are `<dir>:<root>[:<label>]`, <dir> relative to --nto-root (e.g. vac/A_job_0093).  Row text: panel letter,
label and root; right cell carries lambda, f (length) and the pair-1 weight parsed from escf.out / dftnto.out.
Run with render_env (needs scikit-image, povray, pillow):
  ~/.conda/envs/render_env/bin/python nto_grid.py --nto-root ~/work_turbomole/artepillin_C_studies/nto \
      --rows vac/N_job_0044:2:N vac/A_job_0093:23:A -o fig_nto_vac --width-mm 178
Writes <out>.png + <out>.eps (PNG inside, Flate) and keeps the per-cell .pov/.png in <out>_cells/.
"""
import argparse
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_nto as rn  # noqa: E402

rs = rn.rs
FONT = "/usr/share/fonts/stix/STIX-Regular.otf"      # Times-metric serif, the only one installed here
FONT_B = "/usr/share/fonts/stix/STIX-Bold.otf"


def root_info(d, root):
    t = open(f"{d}/escf.out").read()
    ev = re.findall(r"Excitation energy / eV:\s+(\S+)", t)
    nm = re.findall(r"Excitation energy / nm:\s+(\S+)", t)
    f = re.findall(r"Oscillator strength:\s+velocity representation:\s+\S+\s+length representation:\s+(\S+)", t)
    w = re.findall(r"^\s+1\s+\S+\s+(\S+)%", open(f"{d}/S{root}/dftnto.out").read(), re.M)
    return dict(ev=float(ev[root - 1]), nm=float(nm[root - 1]), f=float(f[root - 1]), w=float(w[0]) if w else None)


def _extent(args):
    cube, iso = args
    return rn.half_extent(rn.prepare(cube, iso, step=2))


def _render(args):
    cube, iso, out, wpx, ext = args
    sc = rn.prepare(cube, iso, step=1)
    rn.render_scene(sc, out, wpx, ext, vesta=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nto-root", required=True)
    ap.add_argument("--rows", nargs="+", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--iso", type=float, default=0.03)
    ap.add_argument("--width-mm", type=float, default=178)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--pair", type=int, default=1, help="NTO pair (1 = dominant)")
    a = ap.parse_args()

    rows = []
    for r in a.rows:
        p = r.split(":")
        d = os.path.join(a.nto_root, p[0]); root = int(p[1])
        label = p[2] if len(p) > 2 else p[0].split("/")[1].split("_")[0]
        rows.append((label, d, root))
    cells = [(f"{d}/S{root}/nto_{k}_{a.pair}.cub") for _, d, root in rows for k in ("occ", "vir")]
    cdir = a.output + "_cells"; os.makedirs(cdir, exist_ok=True)
    with Pool(a.jobs) as pool:
        exts = pool.map(_extent, [(c, a.iso) for c in cells])
        ext = (max(e[0] for e in exts), max(e[1] for e in exts))
        cell_w = int(round(a.width_mm / 2 / 25.4 * a.dpi))
        outs = []
        for (label, d, root), (co, cv) in zip(rows, zip(cells[::2], cells[1::2])):
            tag = f"{os.path.basename(d)}_S{root}"
            outs += [(co, a.iso, f"{cdir}/{tag}_hole", cell_w, ext), (cv, a.iso, f"{cdir}/{tag}_electron", cell_w, ext)]
        pool.map(_render, outs)

    cell_h = int(round(cell_w * ext[1] / ext[0]))
    px = a.dpi / 72.0
    fs = ImageFont.truetype(FONT, int(round(10 * px))); fb = ImageFont.truetype(FONT_B, int(round(10 * px)))
    head = int(round(18 * px)); foot = int(round(20 * px))
    W, H = 2 * cell_w, head + len(rows) * cell_h + foot
    im = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(im)
    for j, t in enumerate(("Hole (NTO %d, occupied)" % a.pair, "Electron (NTO %d, virtual)" % a.pair)):
        dr.text((j * cell_w + cell_w // 2, head // 2), t, font=fs, fill="black", anchor="mm")
    for i, (label, d, root) in enumerate(rows):
        tag = f"{os.path.basename(d)}_S{root}"
        y0 = head + i * cell_h
        for j, k in enumerate(("hole", "electron")):
            im.paste(Image.open(f"{cdir}/{tag}_{k}.png").convert("RGB").resize((cell_w, cell_h)), (j * cell_w, y0))
        info = root_info(d, root)
        letter = "abcdefghijklmnopqrstuvwxyz"[i]
        dr.text((int(2 * px), y0 + int(2 * px)), f"{letter})", font=fb, fill="black")
        dr.text((int(16 * px), y0 + int(2 * px)), f"{label}, S{root}", font=fs, fill="black")
        txt = f"{info['nm']:.0f} nm, f = {info['f']:.3f}" + (f", {info['w']:.1f} %" if info["w"] else "")
        dr.text((W - int(2 * px), y0 + int(2 * px)), txt, font=fs, fill="black", anchor="ra")
    # legend row: phases and isovalue
    cy = H - foot // 2; r = int(4 * px)
    x = int(W / 2 - 60 * px)
    for col, name in ((rn.COLOR_POS, "+"), (rn.COLOR_NEG, "−")):
        dr.ellipse((x - r, cy - r, x + r, cy + r), fill=tuple(int(round(c * 255)) for c in col), outline="black")
        dr.text((x + 2 * r, cy), name, font=fs, fill="black", anchor="lm"); x += int(30 * px)
    dr.text((x, cy), f"|ψ| = {a.iso:g} a.u.", font=fs, fill="black", anchor="lm")
    im.save(a.output + ".png", dpi=(a.dpi, a.dpi))
    rs.png_to_eps(a.output + ".png", a.output + ".eps", a.width_mm)
    print(a.output + ".png", im.size, a.output + ".eps")


if __name__ == "__main__":
    main()
