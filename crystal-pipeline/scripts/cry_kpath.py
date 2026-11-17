#!/usr/bin/env python3
"""High-symmetry band path for CRYSTAL `BAND`, same convention as the VASP pipeline
(`gen_kpath.py` in the VASP repo: pymatgen HighSymmKpath, default = Setyawan-Curtarolo 2010,
40 points per segment), converted to CRYSTAL's OWN primitive reciprocal basis.

Why a conversion: pymatgen standardizes the primitive cell (VASP's gen_kpath writes POSCAR_bands and asks
for a new SCF if it differs). CRYSTAL builds its own primitive cell; instead of changing the structure we
map pymatgen's standard primitive lattice onto CRYSTAL's (integer unimodular S, plus rotation), accept the
mapping only if it also maps the ATOMS (so it is a true crystal symmetry, not just a lattice automorphism),
and express every k point as f_cry = f_std . S^-T.

Input: crystal.out of the SCF (last "DIRECT LATTICE VECTORS CARTESIAN COMPONENTS" + "CARTESIAN COORDINATES
- PRIMITIVE CELL" = geometry used for fort.9). Output: KPATH_CRYSTAL next to it, read by
`cry_props.py --kpath-file` (BAND segments) and by `cry_parse.py bands` (tick labels).

Needs pymatgen: ~/micromamba/envs/render_env/bin/python
Usage: render_env/bin/python cry_kpath.py runs/hse_sp/crystal.out [--div 40] [--maxden 96]
"""
import argparse
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from pymatgen.core import Lattice, Structure
from pymatgen.symmetry.bandstructure import HighSymmKpath

SYMBOLS = ("X H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se "
           "Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy "
           "Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf "
           "Es Fm Md No Lr").split()


def read_crystal_out(fn):
    t = Path(fn).read_text(errors="replace")
    j = t.rfind("DIRECT LATTICE VECTORS CARTESIAN COMPONENTS (ANGSTROM)")
    lat = np.array([[float(x) for x in r.split()[:3]] for r in t[j:].splitlines()[2:5]])
    nat = int(re.findall(r"N\. OF ATOMS PER CELL\s+(\d+)", t)[-1])
    k = t.rfind("CARTESIAN COORDINATES - PRIMITIVE CELL")
    rows = re.findall(r"^\s+\d+\s+(\d+)\s+[A-Z]+\s+(\S+)\s+(\S+)\s+(\S+)\s*$", t[k:], re.M)[:nat]
    if len(rows) != nat:
        sys.exit(f"read {len(rows)} atoms, expected {nat}")
    z = [int(r[0]) for r in rows]
    z = [x % 100 if x > 100 else x for x in z]
    cart = np.array([[float(x) for x in r[1:]] for r in rows])
    return Structure(Lattice(lat), [SYMBOLS[x] for x in z], cart, coords_are_cartesian=True)


def atoms_match(fa, sa, fb, sb, tol=1e-3):
    """Same structure up to a global translation (fractional coords in the SAME lattice)?"""
    for i in range(len(fb)):
        if sb[i] != sa[0]:
            continue
        t = fb[i] - fa[0]
        moved = fa + t
        ok = True
        for x, s in zip(moved, sa):
            d = fb - x
            d -= np.round(d)
            hit = np.where((np.linalg.norm(d, axis=1) < tol) & (np.array(sb) == s))[0]
            if len(hit) == 0:
                ok = False
                break
        if ok:
            return True
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scf_out")
    p.add_argument("--div", type=int, default=40, help="points per segment (VASP gen_kpath default 40)")
    p.add_argument("--maxden", type=int, default=96, help="max denominator for each coordinate (ISS = lcm)")
    p.add_argument("--symprec", type=float, default=1e-3)
    p.add_argument("-o", "--output", help="default: KPATH_CRYSTAL next to scf_out")
    a = p.parse_args()

    s = read_crystal_out(a.scf_out)
    kp = HighSymmKpath(s, symprec=a.symprec)  # default path_type = setyawan_curtarolo (as gen_kpath.py)
    std = kp.prim
    S_found = None
    for _, _, S in std.lattice.find_all_mappings(s.lattice, ltol=1e-4, atol=1e-3):
        S = np.array(S, dtype=float)  # std_rows = S @ cry_rows (up to rotation)
        if abs(abs(np.linalg.det(S)) - 1) > 1e-6:
            continue
        f_std_from_cry = s.frac_coords @ np.linalg.inv(S)
        if atoms_match(f_std_from_cry, [x.specie.symbol for x in s], std.frac_coords,
                       [x.specie.symbol for x in std]):
            S_found = S
            break
    if S_found is None:
        sys.exit("no lattice mapping between pymatgen's standard primitive cell and CRYSTAL's maps the atoms")
    to_cry = np.linalg.inv(S_found).T

    kpts = kp.kpath["kpoints"]
    segs = []
    for branch in kp.kpath["path"]:
        for A, B in zip(branch[:-1], branch[1:]):
            segs.append((A, B))
    frac = {lab: np.array(kpts[lab]) @ to_cry for lab in {x for sg in segs for x in sg}}
    # rational approximation -> common ISS
    rat = {lab: [Fraction(float(x)).limit_denominator(a.maxden) for x in v] for lab, v in frac.items()}
    err = max(abs(float(r) - x) for lab in frac for r, x in zip(rat[lab], frac[lab]))
    iss = 1
    for v in rat.values():
        for f in v:
            iss = iss * f.denominator // math.gcd(iss, f.denominator)
    lab = lambda x: "G" if x in ("\\Gamma", "Γ", "GAMMA") else x.replace("_", "").replace("\\", "")
    out = Path(a.output) if a.output else Path(a.scf_out).parent / "KPATH_CRYSTAL"
    lines = [f"# Setyawan-Curtarolo path (pymatgen HighSymmKpath) in CRYSTAL primitive reciprocal basis",
             f"# space group {kp.prim.get_space_group_info()}, branches {kp.kpath['path']}",
             f"# max rational-approximation error {err:.2e} (fractional); div per segment {a.div}",
             f"ISS {iss}", f"DIV {a.div}"]
    for A, B in segs:
        ia = [int(f * iss) for f in rat[A]]
        ib = [int(f * iss) for f in rat[B]]
        lines.append(" ".join(map(str, ia + ib)) + f" {lab(A)} {lab(B)}")
    out.write_text("\n".join(lines) + "\n")
    print(f"{a.scf_out}: {kp.prim.get_space_group_info()} path {kp.kpath['path']} -> {len(segs)} segments, "
          f"ISS {iss}, max approx error {err:.1e}. Written {out}")
    if err > 2e-3:
        print("WARNING: irrational special points approximated; raise --maxden if needed", file=sys.stderr)


if __name__ == "__main__":
    main()
