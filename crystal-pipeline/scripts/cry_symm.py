#!/usr/bin/env python3
"""Detect the space group (spglib) of a structure and write a CRYSTAL `crygeo` block with the
standardized conventional cell and the ASYMMETRIC UNIT (so CRYSTAL uses the full symmetry).

Inputs: POSCAR/CONTCAR, CIF (anything pymatgen reads), fort.34, or a P1 crygeo / CRYSTAL INPUT
(first block, space group 1). ECP-flagged atomic numbers (Z>200, e.g. 247 = Ag) are kept.

Needs pymatgen + spglib: ~/micromamba/envs/render_env/bin/python (pymatgen 2026.9.24, spglib 2.8.0).

Verification (--verify): runs CRYSTAL with TESTGEOM on the new block (seconds, serial) and checks that
the primitive cell it builds has the same volume, composition and sorted nearest-neighbour distances
as the spglib primitive cell of the input (tolerance --verify-tol A). Mismatch usually means a setting/origin choice issue (IFHR/IFSO, manual p.19).

Usage:
  render_env/bin/python cry_symm.py INPUT_or_POSCAR -o mat.crygeo [--symprec 1e-3] [--verify]
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import spglib

SYMBOLS = ("X H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se "
           "Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy "
           "Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf "
           "Es Fm Md No Lr").split()


def cellpar_to_vec(a, b, c, al, be, ga):
    al, be, ga = np.radians([al, be, ga])
    v1 = [a, 0, 0]
    v2 = [b * np.cos(ga), b * np.sin(ga), 0]
    cx = c * np.cos(be)
    cy = c * (np.cos(al) - np.cos(be) * np.cos(ga)) / np.sin(ga)
    return np.array([v1, v2, [cx, cy, np.sqrt(c * c - cx * cx - cy * cy)]])


def read_any(path):
    """Return lattice (3x3, A), fractional positions, CRYSTAL Z list."""
    p = Path(path)
    txt = p.read_text(errors="replace")
    lines = [l for l in txt.splitlines() if l.strip()]
    i0 = next((i for i, l in enumerate(lines[:3]) if l.split()[0].upper() == "CRYSTAL"), None)
    if i0 is not None:  # P1 crygeo or full INPUT
        sg = lines[i0 + 2].split()[0]
        if sg != "1":
            sys.exit("crygeo input must be P1 (space group 1); for symmetric blocks there is nothing to do")
        par = [float(x) for x in lines[i0 + 3].split()]
        nat = int(lines[i0 + 4].split()[0])
        at = [l.split() for l in lines[i0 + 5:i0 + 5 + nat]]
        return cellpar_to_vec(*par), np.array([[float(x) for x in a[1:4]] for a in at]), [int(a[0]) for a in at]
    if "fort.34" in p.name or p.suffix == ".34":
        L = txt.splitlines()
        lat = np.array([[float(x) for x in L[i].split()[:3]] for i in (1, 2, 3)])
        nsym = int(L[4].split()[0])
        k = 5 + 4 * nsym
        nat = int(L[k].split()[0])
        at = [L[k + 1 + j].split() for j in range(nat)]
        cart = np.array([[float(x) for x in a[1:4]] for a in at])
        if nsym > 1:
            sys.exit("fort.34 already carries symmetry operators; use it directly with EXTERNAL")
        return lat, cart @ np.linalg.inv(lat), [int(a[0]) for a in at]
    from pymatgen.core import Structure
    s = Structure.from_file(str(p))
    return s.lattice.matrix, s.frac_coords, [site.specie.Z for site in s]


def crygeo_lines(sg, lat_std, pos, zs):
    a, b, c = np.linalg.norm(lat_std, axis=1)
    ang = lambda u, v: np.degrees(np.arccos(np.dot(u, v) / np.linalg.norm(u) / np.linalg.norm(v)))
    al, be, ga = ang(lat_std[1], lat_std[2]), ang(lat_std[0], lat_std[2]), ang(lat_std[0], lat_std[1])
    if sg <= 2:
        par = [a, b, c, al, be, ga]
    elif sg <= 15:
        par = [a, b, c, be]
    elif sg <= 74:
        par = [a, b, c]
    elif sg <= 194:
        par = [a, c]
    else:
        par = [a]
    out = ["CRYSTAL", "0 0 0", str(sg), " ".join(f"{x:.8f}" for x in par), str(len(zs))]
    out += [f"{z} {x:.12f} {y:.12f} {w:.12f}" for z, (x, y, w) in zip(zs, pos % 1.0)]
    return out


def verify(geo, lat_in, pos_in, z_in, tol):
    """TESTGEOM run; compare generated cell atoms with the input ones (by cartesian distance, PBC)."""
    root = os.environ.get("CRY23_ROOT")
    if not root:
        print("verify skipped: load modmat/crystal/23.1.0.1 first", file=sys.stderr)
        return None
    exe = Path(root) / "bin/Linux-ifort_i64/v1.0.1/crystal"
    with tempfile.TemporaryDirectory() as d:
        Path(d, "INPUT").write_text("\n".join(["verify"] + geo + ["TESTGEOM", "END", "END"]) + "\n")
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = "/opt/intel/oneapi/compiler/2026.2/lib:" + env.get("LD_LIBRARY_PATH", "")
        r = subprocess.run(f"{exe} < INPUT", shell=True, cwd=d, env=env, capture_output=True, text=True, timeout=120)
        t = r.stdout
    m = list(re.finditer(r"ATOMS IN THE UNIT CELL:\s+(\d+)", t))
    if not m:
        print(t[-1500:], file=sys.stderr)
        sys.exit("verify: CRYSTAL did not print the atom table")
    nat = int(m[-1].group(1))
    j = t.rfind("DIRECT LATTICE VECTORS CARTESIAN COMPONENTS (ANGSTROM)")
    lat_c = np.array([[float(x) for x in r.split()[:3]] for r in t[j:].splitlines()[2:5]])
    k = t.rfind("CARTESIAN COORDINATES - PRIMITIVE CELL")
    rows = re.findall(r"^\s+\d+\s+(\d+)\s+[A-Z]+\s+(\S+)\s+(\S+)\s+(\S+)\s*$", t[k:], re.M)[:nat]
    cart_c = np.array([[float(x) for x in r[1:]] for r in rows])
    zc = [int(r[0]) for r in rows]
    ok = nat == len(z_in)
    # compare in a lattice-independent way: interatomic distance spectra per species pair is overkill;
    # use volume + per-element counts + sorted nearest-neighbour distances
    vol_in, vol_c = abs(np.linalg.det(lat_in)), abs(np.linalg.det(lat_c))
    cnt = lambda zs: sorted((z, zs.count(z)) for z in set(zs))
    ok &= cnt(zc) == cnt(z_in) and abs(vol_in - vol_c) / vol_in < 1e-4

    def nn(lat, cart):
        f = cart @ np.linalg.inv(lat)
        d = []
        for i in range(len(f)):
            df = f - f[i]
            df -= np.round(df)
            r = np.linalg.norm(df @ lat, axis=1)
            d.append(np.sort(r)[1])
        return np.sort(d)
    dn = np.max(np.abs(nn(lat_in, pos_in @ lat_in) - nn(lat_c, cart_c))) if ok else float("inf")
    ok &= dn < tol
    print(f"verify: CRYSTAL cell atoms {nat} (input {len(z_in)}), V {vol_c:.4f} vs {vol_in:.4f} A^3, "
          f"max |d_nn| diff {dn:.2e} A -> {'OK' if ok else 'MISMATCH'}")
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("structure")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--symprec", type=float, default=1e-3, help="spglib tolerance in A")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--verify-tol", type=float, default=2e-3)
    a = p.parse_args()

    lat, pos, zs = read_any(a.structure)
    zkey = {z % 100 if z > 100 else z: z for z in zs}  # keep ECP flag per element
    numbers = [z % 100 if z > 100 else z for z in zs]
    ds = spglib.get_symmetry_dataset((lat, pos, numbers), symprec=a.symprec)
    if ds is None:
        sys.exit("spglib failed")
    std_lat, std_pos, std_num = ds.std_lattice, ds.std_positions, ds.std_types
    ds2 = spglib.get_symmetry_dataset((std_lat, std_pos, std_num), symprec=a.symprec)
    asym = sorted(set(ds2.equivalent_atoms))
    geo = crygeo_lines(int(ds.number), std_lat, std_pos[asym], [zkey[int(std_num[i])] for i in asym])
    Path(a.output).write_text("\n".join(geo) + "\n")
    print(f"{a.structure}: space group {ds.international} ({ds.number}), {len(zs)} atoms in -> "
          f"{len(std_num)} in conventional cell, {len(asym)} in asymmetric unit, "
          f"{len(ds.rotations)} operations (input cell). Written {a.output}")
    if len(std_num) != len(zs):
        print("note: conventional cell differs from the input cell (centred lattice or supercell input); "
              "CRYSTAL builds the primitive cell itself", file=sys.stderr)
    if a.verify:  # CRYSTAL works in the PRIMITIVE cell: compare with the spglib primitive of the input
        plat, ppos, pnum = spglib.standardize_cell((lat, pos, numbers), to_primitive=True, symprec=a.symprec)
        ok = verify(geo, plat, ppos, [zkey[int(n)] for n in pnum], a.verify_tol)
        if ok is False:
            sys.exit(1)


if __name__ == "__main__":
    main()
