#!/usr/bin/env python3
"""Render a Gaussian-cube orbital/NTO (TURBOMOLE `$pointval ... fmt=cub`) as a VESTA-style 3D figure:
ball-and-stick molecule + translucent +/- isosurfaces (yellow = +, cyan = -), POV-Ray, EPS wrapping a PNG, plus a .vesta (cube imported) for hand adjustment.

Reuses the style, orientation, POV-Ray runner and EPS writer of academic-figure-skill/scripts/render_structures.py.
Run with render_env (povray, ase, pillow, scipy, scikit-image):
  ~/.conda/envs/render_env/bin/python render_nto.py nto_vir_1.cub --iso 0.02 --width-mm 178 --dpi 300 -o conf_1_LUMO
"""
import argparse
import os
import sys

import numpy as np
from ase import Atoms
from skimage.measure import marching_cubes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/skills/academic-figure-skill/scripts"))
import render_structures as rs  # noqa: E402

BOHR = 0.529177210903
COLOR_POS = (1.00, 1.00, 0.60)   # sRGB, yellow
COLOR_NEG = (0.62, 1.00, 1.00)   # sRGB, cyan
TRANSMIT = 0.55


def read_cube(path):
    with open(path) as fh:
        fh.readline(); fh.readline()
        t = fh.readline().split()
        nat, origin = int(t[0]), np.array(t[1:4], float)
        axes, n = [], []
        for _ in range(3):
            t = fh.readline().split()
            n.append(int(t[0])); axes.append([float(x) for x in t[1:4]])
        Z, xyz = [], []
        for _ in range(abs(nat)):
            t = fh.readline().split()
            Z.append(int(t[0])); xyz.append([float(x) for x in t[2:5]])
        vals = np.array(fh.read().split(), float).reshape(n)
    unit = BOHR if n[0] > 0 else 1.0
    return (Atoms(numbers=Z, positions=np.array(xyz) * unit), origin * unit,
            np.array(axes) * unit, vals)


def _lin(c):
    return tuple(rs._srgb_to_linear(x) for x in c)


def mesh_pov(verts, faces, normals, color):
    r, g, b = _lin(color)
    v = ",".join(rs._vec(p) for p in verts)
    n = ",".join(rs._vec(p) for p in normals)
    f = ",".join(f"<{a},{b_},{c}>" for a, b_, c in faces)
    return (f"mesh2 {{ vertex_vectors {{ {len(verts)},{v} }} normal_vectors {{ {len(verts)},{n} }} "
            f"face_indices {{ {len(faces)},{f} }} "
            f"texture {{ pigment {{ rgbt <{r:.4f},{g:.4f},{b:.4f},{TRANSMIT}> }} "
            f"finish {{ ambient 0.3 diffuse 0.6 specular 0.2 roughness 0.02 }} }} no_shadow }}")


def write_vesta_cube(atoms0, bl, cube, origin, axes, vals, path, title):
    """VESTA file for hand adjustment: structure in the cube's own frame (not re-oriented), cell = grid
    box, volumetric data imported from the cube (relative path). The isosurface itself (ISURF) is set in
    VESTA: Properties > Isosurfaces, 'both signs', level = --iso, yellow/cyan, opacity ~45 %."""
    import re
    n = np.array(vals.shape)
    cell = np.linalg.norm(axes, axis=1) * n               # A; cube axes are orthogonal in TURBOMOLE
    tmp = atoms0.copy()
    tmp.positions = atoms0.positions - origin             # origin -> 0 so fractional = pos / cell
    rs.write_vesta(tmp, bl, path, title)
    txt = open(path).read()
    txt = re.sub(r"(CELLP\n)\s*\S+\s+\S+\s+\S+", lambda m: m.group(1) + f"  {cell[0]:.6f}   {cell[1]:.6f}   {cell[2]:.6f}", txt, count=1)
    k = {"i": 0}
    def frac(m):
        i = k["i"]; k["i"] += 1
        f = tmp.positions[i] / cell
        return f"{m.group(1)}{f[0]:.6f}   {f[1]:.6f}   {f[2]:.6f}{m.group(2)}"
    txt = re.sub(r"(\n\s+\d+ [A-Z][a-z]? +\S+ +1\.0000   )\S+   \S+   \S+(    1a       1)", frac, txt)
    rel = os.path.relpath(cube, os.path.dirname(os.path.abspath(path)))
    txt = txt.replace("\nGROUP", f"\nIMPORT_DENSITY 1\n+1.000000 {rel}\n\nGROUP", 1)
    open(path, "w").write(txt)


def prepare(cube, iso, step=1):
    """Read the cube, orient the molecule, build the +/- meshes in the oriented frame, centre on the atoms' bbox."""
    atoms0, origin, axes, vals = read_cube(cube)
    # round before orienting: the SVD normal has an arbitrary sign that flips with 1e-6 noise, which made
    # the hole and electron cubes of the same molecule come out rotated 180 degrees from each other
    ar = atoms0.copy(); ar.positions = np.round(atoms0.positions, 3)
    atoms = rs.orient(ar)
    # affine map original -> oriented frame (orient() is a rigid transform), fit on the atoms
    P = np.hstack([atoms0.positions, np.ones((len(atoms0), 1))])
    M = np.linalg.lstsq(P, atoms.positions, rcond=None)[0]
    parts = []
    for sign, col in ((+1, COLOR_POS), (-1, COLOR_NEG)):
        if np.max(sign * vals) < iso:
            continue
        v, f, nrm, _ = marching_cubes(sign * vals, iso, spacing=(1, 1, 1), step_size=step)
        cart = origin + v @ axes                       # index -> Angstrom
        cart = np.hstack([cart, np.ones((len(cart), 1))]) @ M
        nr = nrm @ axes @ M[:3]                         # outward normals, rotated (rigid map)
        nr = nr / np.linalg.norm(nr, axis=1, keepdims=True)
        parts.append([cart, f, nr, col])
    c = (atoms.positions[:, :2].max(0) + atoms.positions[:, :2].min(0)) / 2
    shift = np.array([c[0], c[1], 0.0])
    atoms.positions = atoms.positions - shift
    for p in parts:
        p[0] = p[0] - shift
    return dict(atoms0=atoms0, atoms=atoms, parts=parts, origin=origin, axes=axes, vals=vals, cube=cube)


def half_extent(sc):
    allp = np.vstack([sc["atoms"].positions] + [p[0] for p in sc["parts"]])
    return np.abs(allp[:, 0]).max() + 0.3, np.abs(allp[:, 1]).max() + 0.3


def render_scene(sc, out, wpx, ext, vesta=True):
    """POV-Ray render with a window of half-sizes `ext` (Angstrom) -> out.pov/.png (+ .vesta)."""
    hpx = max(1, int(round(wpx * ext[1] / ext[0])))
    pov = out + ".pov"
    rs.write_pov(sc["atoms"], rs.bonds(sc["atoms"]), pov, wpx, hpx, extents=ext)
    with open(pov, "a") as fh:
        for cart, f, nr, col in sc["parts"]:
            fh.write(mesh_pov(cart, f, nr, col) + "\n")
    ok, msg = rs.render(pov, out + ".png", wpx, hpx)
    if not ok:
        sys.exit("povray failed: " + msg)
    if vesta:
        write_vesta_cube(sc["atoms0"], rs.bonds(sc["atoms0"]), sc["cube"], sc["origin"], sc["axes"],
                         sc["vals"], out + ".vesta", os.path.basename(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cube")
    ap.add_argument("--iso", type=float, default=0.03, help="isovalue (|psi|, a.u.) for both lobes")
    ap.add_argument("--width-mm", type=float, default=178)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("-o", "--output", required=True, help="prefix; writes .pov/.png/.eps/.vesta")
    ap.add_argument("--step", type=int, default=1, help="marching-cubes stride (2 = faster, coarser)")
    a = ap.parse_args()
    sc = prepare(a.cube, a.iso, a.step)
    wpx = int(round(a.width_mm / 25.4 * a.dpi))
    render_scene(sc, a.output, wpx, half_extent(sc))
    rs.png_to_eps(a.output + ".png", a.output + ".eps", a.width_mm)
    print(a.output + ".png", a.output + ".eps")


if __name__ == "__main__":
    main()
