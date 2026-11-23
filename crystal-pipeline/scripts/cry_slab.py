#!/usr/bin/env python3
"""
cry_slab.py -- enumerate and cut slabs with CRYSTAL's own SLABCUT (true 2D, no vacuum).

For each plane (Miller indices of the CONVENTIONAL cell, as CRYSTAL reads them):
  1. SLABINFO (TESTGEOM run, < 1 s) -> atomic layers of one period along the normal.
  2. Every (ISUP, NL) whose layer content has the bulk stoichiometry and thickness
     <= --max-thick is cut with SLABCUT + TESTGEOM (CRYSTAL derives the layer group).
  3. Kept only if SYMMETRIC: the layer group has an operation with z -> -z
     (inversion, mirror in the slab plane or in-plane 2-fold axis), so both faces
     are the same termination and gamma = (E_slab - n E_bulk) / 2A is one surface.
     Symmetric + stoichiometric => no dipole along z (Tasker I/II).
  4. Ranked per plane by broken cation-anion bonds per surface area
     (bulk coordination - slab coordination, per face, per A^2).

Terminations are identified by the top-layer pattern; for each termination the
thickness series (all symmetric NL up to --max-thick) is listed.

Output (--outdir): slabs.csv (all symmetric candidates), and for each candidate
<hkl>_t<term>_nl<NL>/{GEOM.d12-part, slab.xyz} where GEOM.d12-part is the geometry
block to paste after the fort.34 EXTERNAL keyword (SLABCUT h k l / ISUP NL).

Needs the CRYSTAL module environment (crystalOMP binary) -- runs only TESTGEOM jobs:
  python3 cry_slab.py --geom fort.34 --planes "1,0,1;0,0,1;1,0,0" --max-thick 20 --outdir slabs
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

SYM = {8: "O", 22: "Ti", 40: "Zr", 47: "Ag", 34: "Se", 12: "Mg"}


def binary():
    root = os.environ.get("CRY23_ROOT")
    if not root:
        raise SystemExit("CRY23_ROOT not set: module load modmat/crystal/23.1.0.1")
    return f"{root}/bin/Linux-ifort_i64_omp/v1.0.1/crystalOMP"


def run_testgeom(geom34, body, workdir):
    """Run crystalOMP on 'EXTERNAL + body + TESTGEOM'; return output text."""
    wd = Path(workdir)
    shutil.copy(geom34, wd / "fort.34")
    (wd / "INPUT").write_text("slab test\nEXTERNAL\n" + body + "TESTGEOM\nEND\n")
    env = dict(os.environ, OMP_NUM_THREADS="2")
    with open(wd / "INPUT") as fi:
        r = subprocess.run([binary()], stdin=fi, capture_output=True, text=True, cwd=wd, env=env, timeout=120)
    return r.stdout + r.stderr


def parse_slabinfo(out):
    """Layers of one period: list of (z, [atomic numbers]), top first; period along normal."""
    layers = []
    lines = out.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"\s*LAYER\s+\d+\s+Z=\s*(\S+);", ln)
        if m:
            z = float(m.group(1))
            zs = []
            j = i + 1
            while j < len(lines) and re.match(r"\s+\d+\s+\d+\s+\S+\s+\S+\s+\S+\s*$", lines[j]):
                zs.append(int(lines[j].split()[1]))
                j += 1
            layers.append((z, zs))
    m = re.search(r"B3 Z PROJECTION\s+(\S+)", out)
    area = float(re.search(r"AREA OF THE 2D CELL\s+(\S+)", out).group(1))
    return layers, float(m.group(1)), area


def parse_slab(out):
    """Atoms (Z, xyz), 2D cell vectors, symmetry rotation matrices of the cut slab."""
    if "SLAB GENERATED" not in out:
        return None
    seg = out.split("SLAB GENERATED", 1)[1]
    ops = []
    m = re.search(r"\*\*\*\*\s+(\d+) SYMMOPS", seg)
    if m:
        n = int(m.group(1))
        tail = seg[m.end():].splitlines()
        rows = [l for l in tail if re.match(r"\s+\d+\s+\d+\s+-?\d+\.\d\d", l)][:n]
        for l in rows:
            v = [float(x) for x in l.split()[2:14]]
            ops.append(np.array(v[:9]).reshape(3, 3))
    m = re.search(r"DIRECT LATTICE VECTORS CARTESIAN COMPONENTS \(ANGSTROM\)\s*\n.*\n(.*)\n(.*)\n", seg)
    a1 = np.array([float(x) for x in m.group(1).split()])
    a2 = np.array([float(x) for x in m.group(2).split()])
    atoms = []
    body = seg.split("CARTESIAN COORDINATES - PRIMITIVE CELL", 1)[1].splitlines()[4:]
    for l in body:
        p = l.split()
        if len(p) == 6 and p[0].isdigit():
            atoms.append((int(p[1]), np.array([float(x) for x in p[3:6]])))
        else:
            break
    return atoms, a1[:2], a2[:2], ops


def coordination(atoms, a1, a2, cat, an, rcut):
    """Cation-anion bonds within rcut in the 2D-periodic slab."""
    cpos = [x for z, x in atoms if z == cat]
    apos = [x for z, x in atoms if z == an]
    shifts = [i * np.r_[a1, 0] + j * np.r_[a2, 0] for i in range(-2, 3) for j in range(-2, 3)]
    per = []
    for c in cpos:
        per.append(sum(1 for a in apos for s in shifts if np.linalg.norm(a + s - c) < rcut))
    return per


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--geom", required=True, help="bulk fort.34 (converged geometry)")
    ap.add_argument("--planes", required=True, help='"h,k,l;h,k,l" (conventional cell)')
    ap.add_argument("--max-thick", type=float, default=20.0, help="max slab thickness (A, atom z range)")
    ap.add_argument("--min-thick", type=float, default=0.0)
    ap.add_argument("--cation", type=int, default=22)
    ap.add_argument("--anion", type=int, default=8)
    ap.add_argument("--rcut", type=float, default=2.3, help="cation-anion bond cutoff (A)")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()

    out_root = Path(a.outdir)
    out_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="cryslab_", dir=out_root))
    geom = Path(a.geom).resolve()

    rows = []
    for plane in [tuple(int(x) for x in p.split(",")) for p in a.planes.split(";") if p.strip()]:
        tag = "".join(str(h) if h >= 0 else f"m{-h}" for h in plane)
        out = run_testgeom(geom, "SLABINFO\n%d %d %d\n" % plane, tmp)
        layers, dz, area = parse_slabinfo(out)
        P = len(layers)
        comp = Counter(z for _, zs in layers for z in zs)
        ratio = comp[a.anion] / comp[a.cation]
        print(f"({tag}) period {P} layers, {dz:.3f} A, area {area:.3f} A2, period comp {dict(comp)}")
        seen = 0
        for isup in range(1, P + 1):
            for nl in range(1, 40 * P):
                idx = [(isup - 1 + k) for k in range(nl)]
                thick = layers[(isup - 1) % P][0] - (layers[idx[-1] % P][0] - (idx[-1] // P) * dz)
                if thick > a.max_thick + 1e-6:
                    break
                if thick < a.min_thick:
                    continue
                c = Counter(z for k in idx for z in layers[k % P][1])
                if c[a.cation] == 0 or abs(c[a.anion] / c[a.cation] - ratio) > 1e-9:
                    continue
                res = parse_slab(run_testgeom(geom, "SLABCUT\n%d %d %d\n%d %d\n" % (plane + (isup, nl)), tmp))
                seen += 1
                if res is None:
                    continue
                atoms, a1, a2, ops = res
                sym = any(abs(R[2, 2] + 1) < 1e-6 for R in ops)
                if not sym:
                    continue
                per = coordination(atoms, a1, a2, a.cation, a.anion, a.rcut)
                nb, ncat = sum(per), len(per)
                zs = [x[2] for _, x in atoms]
                top = sorted(atoms, key=lambda t: -t[1][2])
                ztop = top[0][1][2]
                term = "".join(SYM.get(z, str(z)) for z, x in top if ztop - x[2] < 0.6)
                A2 = abs(np.cross(a1, a2))
                rows.append(dict(hkl=plane, cnmax=max(per), plane=tag, isup=isup, nl=nl, natoms=len(atoms), n_fu=ncat,
                                 thick=round(max(zs) - min(zs), 3), area=round(A2, 3), nops=len(ops),
                                 bonds=nb, top=term, _atoms=atoms, _a=(a1, a2)))
        print(f"   {seen} stoichiometric cuts tested")

    # broken bonds: bulk cation coordination = max per-cation coordination over all candidates' interiors
    # (anatase/rutile: 6); taken as the most common integer of bonds/ncat in the thickest slabs.
    cn_bulk = max((r["cnmax"] for r in rows), default=None)   # interior cations keep the bulk CN
    for r in rows:
        r["broken_per_A2"] = round((cn_bulk * r["n_fu"] - r["bonds"]) / (2 * r["area"]), 4)
    # termination id per plane: by (isup mod pattern) -> group by top pattern + broken density
    keyf = lambda r: (r["plane"], r["broken_per_A2"], r["top"])
    terms = {}
    for r in sorted(rows, key=lambda r: (r["plane"], r["broken_per_A2"], r["thick"])):
        k = keyf(r)
        if k not in terms:
            terms[k] = 1 + sum(1 for kk in terms if kk[0] == r["plane"])
        r["term"] = terms[k]
    rows.sort(key=lambda r: (r["plane"], r["term"], r["thick"], r["isup"]))
    uniq, seen_k = [], set()          # equivalent ISUP give the same slab: keep the first
    for r in rows:
        k = (r["plane"], r["term"], r["nl"])
        if k not in seen_k:
            seen_k.add(k)
            uniq.append(r)
    rows = uniq

    fields = ["plane", "term", "top", "broken_per_A2", "isup", "nl", "natoms", "n_fu", "thick", "area", "nops"]
    with open(out_root / "slabs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        d = out_root / f"{r['plane']}_t{r['term']}_nl{r['nl']:02d}"
        d.mkdir(exist_ok=True)
        (d / "GEOM.d12-part").write_text("EXTERNAL\nSLABCUT\n%d %d %d\n%d %d\n" % (r["hkl"] + (r["isup"], r["nl"])))
        with open(d / "slab.xyz", "w") as f:
            f.write(f"{len(r['_atoms'])}\n{r['plane']} term {r['term']} ISUP {r['isup']} NL {r['nl']} "
                    f"a1={r['_a'][0].tolist()} a2={r['_a'][1].tolist()}\n")
            for z, x in r["_atoms"]:
                f.write(f"{SYM.get(z, z)} {x[0]:.6f} {x[1]:.6f} {x[2]:.6f}\n")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"bulk cation CN = {cn_bulk}; {len(rows)} symmetric stoichiometric slabs -> {out_root}/slabs.csv")
    for r in rows:
        print("  {plane:>4} t{term} top={top:<6} broken/A2={broken_per_A2:<7} ISUP={isup:<3} NL={nl:<3} "
              "nat={natoms:<4} thick={thick:<7} area={area:<8} ops={nops}".format(**r))


if __name__ == "__main__":
    main()
