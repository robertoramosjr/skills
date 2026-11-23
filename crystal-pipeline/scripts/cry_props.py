#!/usr/bin/env python3
"""Build the CRYSTAL23 `properties` input (d3) for band structure and DOS/PDOS from a finished SCF.

Reads the SCF output (crystal.out) for: electrons per cell, number of AOs, atom list (unit cell),
SCF shrinking factors and spin. Writes <rundir>/PROPS (run with: properties < PROPS, fort.9 present).

Order enforced (manual p.310/320/346): BAND -> NEWK -> DOSS (BAND after NEWK destroys NEWK data).
Defaults follow the user's VASP rules: DOS k-net = 3x the SCF net per axis, NPT = 6001 (NEDOS=6001).

Usage (default route = VASP convention, Setyawan-Curtarolo path from cry_kpath.py):
  render_env/bin/python cry_kpath.py runs/hse_sp/crystal.out        # -> runs/hse_sp/KPATH_CRYSTAL
  cry_props.py --scf-out runs/hse_sp/crystal.out --what both --kpath-file runs/hse_sp/KPATH_CRYSTAL
  alternatives: --path "G X;X W" (labels of manual Tables 14.1/14.2) or --path-frac "0 0 0 1/2 0 1/2;..."
  options: [--newk-mult 3] [--bands-below 40 --bands-above 40] [--nsub N]
Band labels with ISS=0 must exist in manual Tables 14.1/14.2 for the Bravais lattice
(grep -n "Table 14.1" references/CRYSTAL23_Manual.md); otherwise use --path-frac.
"""
import argparse
import math
import re
import sys
from fractions import Fraction
from pathlib import Path


def parse_scf(out):
    t = Path(out).read_text(errors="replace")
    nel = int(re.findall(r"N\. OF ELECTRONS PER CELL\s+(\d+)", t)[-1])
    nao = int(re.findall(r"NUMBER OF AO\s+(\d+)", t)[-1])
    k = [int(x) for x in re.findall(r"SHRINK\. FACT\.\(MONKH\.\)\s+(\d+)\s+(\d+)\s+(\d+)", t)[-1]]
    spin = bool(re.search(r"TYPE OF CALCULATION :\s+UNRESTRICTED|SPIN POLARIZED|UNRESTRICTED OPEN SHELL", t))
    # last "ATOMS IN THE ASYMMETRIC UNIT ... ATOMS IN THE UNIT CELL" table = current geometry
    blocks = list(re.finditer(r"ATOMS IN THE ASYMMETRIC UNIT\s+\d+ - ATOMS IN THE UNIT CELL:\s+(\d+)", t))
    if not blocks:
        sys.exit("atom table not found in SCF output")
    nat = int(blocks[-1].group(1))
    atoms = re.findall(r"^\s+(\d+)\s+[TF]\s+(\d+)\s+([A-Z]+)\s", t[blocks[-1].end():], re.M)[:nat]
    if len(atoms) != nat:
        sys.exit(f"parsed {len(atoms)} atoms, expected {nat}")
    return nel, nao, k, spin, [(int(i), sym.capitalize()) for i, _, sym in atoms]


def band_lines(args):
    if args.kpath_file:  # written by cry_kpath.py (Setyawan-Curtarolo path, CRYSTAL primitive basis)
        iss, div, rows = None, None, []
        for l in Path(args.kpath_file).read_text().splitlines():
            if l.startswith("#") or not l.strip():
                continue
            t = l.split()
            if t[0] == "ISS":
                iss = int(t[1])
            elif t[0] == "DIV":
                div = int(t[1])
            else:
                rows.append(" ".join(t[:6]))
        if args.nsub is None:
            args.nsub = div * len(rows)
        return iss, rows
    if args.path_frac:
        segs = [[Fraction(x) for x in s.split()] for s in args.path_frac.split(";") if s.strip()]
        if any(len(s) != 6 for s in segs):
            sys.exit("--path-frac: 6 fractional numbers per segment (start xyz, end xyz)")
        iss = 1
        for s in segs:
            for f in s:
                iss = iss * f.denominator // math.gcd(iss, f.denominator)
        rows = [" ".join(str(int(f * iss)) for f in s) for s in segs]
        return iss, rows
    segs = [s.split() for s in args.path.split(";") if s.strip()]
    return 0, [" ".join(s) for s in segs]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scf-out", required=True)
    p.add_argument("--what", choices=["dos", "bands", "both"], default="both")
    p.add_argument("--kpath-file", help="KPATH_CRYSTAL from cry_kpath.py (DEFAULT route: same path convention as VASP)")
    p.add_argument("--path", help='labels, ISS=0: "G X;X W"')
    p.add_argument("--path-frac", help='"x1 y1 z1 x2 y2 z2;..." fractions of b1,b2,b3 (e.g. 1/2)')
    p.add_argument("--nsub", type=int, help="total k points along the path (default: DIV x segments, or 400)")
    p.add_argument("--newk-mult", type=int, default=3, help="DOS net = mult x SCF net (user rule: 3)")
    p.add_argument("--newk", type=int, nargs=3, help="explicit DOS net (overrides --newk-mult)")
    p.add_argument("--npt", type=int, default=6001, help="DOS energy points (user rule: 6001)")
    p.add_argument("--npol", type=int, default=18, help="Legendre polynomials (manual: 10-18, <=25)")
    p.add_argument("--bands-below", type=int, default=40)
    p.add_argument("--bands-above", type=int, default=40)
    p.add_argument("--no-pdos", action="store_true", help="total DOS only")
    p.add_argument("-o", "--output", help="default: <dir of scf-out>/PROPS")
    a = p.parse_args()

    nel, nao, kscf, spin, atoms = parse_scf(a.scf_out)
    homo = nel // 2 if not spin else (nel + 1) // 2  # spin: rough window centre; check alpha/beta HOMO in output
    inzb, ifnb = max(1, homo - a.bands_below), min(nao, homo + a.bands_above)
    if inzb == 1:
        print("WARNING: band window starts at band 1: with an all-electron basis (no ECP) this includes core "
              "levels and the 6001-point DOS grid becomes useless (TiO2: 818 meV step). "
              "Use --bands-below to start at the valence/semicore (TiO2 pob-TZVP-rev2: 16).")
    d3 = []
    if a.what in ("bands", "both"):
        if not (a.kpath_file or a.path or a.path_frac):
            p.error("bands need --kpath-file (default route), --path or --path-frac")
        iss, rows = band_lines(a)
        a.nsub = a.nsub or 400
        d3 += ["BAND", "band structure", f"{len(rows)} {iss} {a.nsub} {inzb} {ifnb} 1 0"] + rows
    if a.what in ("dos", "both"):
        kn = a.newk or [a.newk_mult * x for x in kscf]
        if kn[0] == kn[1] == kn[2]:
            d3 += ["NEWK", f"{kn[0]} {2 * kn[0]}", "1 0"]
        else:
            d3 += ["NEWK", f"0 {2 * kn[0]}", f"{kn[0]} {kn[1]} {kn[2]}", "1 0"]
        groups = {}
        for i, s in atoms:
            groups.setdefault(s, []).append(i)
        proj = [] if a.no_pdos else [f"-{len(v)} " + " ".join(map(str, v)) for v in groups.values()]
        d3 += ["DOSS", f"{len(proj)} {a.npt} {inzb} {ifnb} 2 {a.npol} 0"] + proj
    d3 += ["END"]
    out = Path(a.output) if a.output else Path(a.scf_out).parent / "PROPS"
    out.write_text("\n".join(d3) + "\n")
    print(f"written {out}  (electrons {nel}, AO {nao}, HOMO band {homo}, window {inzb}-{ifnb}, "
          f"SCF net {kscf}, PDOS order: {', '.join(groups) if a.what != 'bands' and not a.no_pdos else '-'})")


if __name__ == "__main__":
    main()
