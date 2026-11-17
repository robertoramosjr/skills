#!/usr/bin/env python3
"""Build CRYSTAL23 SCF/optimization inputs (crystal "INPUT" deck, d12) for the pipeline steps.

Steps covered (see SKILL.md):
  kconv    one single-point per k-mesh (run dirs <name>[_lNN]_k<a>x<b>x<c>)     -> step 1
           meshes from --kseries or from VASP-Auto lengths --klengths (same rule as KPOINTS "Auto");
           --kconv-opt runs FULLOPTG per mesh instead of a single point (VASP-rito parity, costly)
  fullopt  OPTGEOM + FULLOPTG  (cell + ions; VASP ISIF=3 analogue)              -> step 2
  atomopt  OPTGEOM + ATOMONLY  (ions only, fixed cell; VASP ISIF=2 analogue)    -> step 3
  sp       single point (writes fort.9 for properties: DOS/bands)               -> step 4

Geometry sources (--geom, format guessed from name or forced with --geom-fmt):
  crygeo  text file holding the CRYSTAL geometry block, from the "CRYSTAL" line to the last atom
          line (space group + asymmetric unit). PREFERRED: keeps the real symmetry.
  fort34  fort.34 written by a previous optimization -> EXTERNAL keyword (file copied as fort.34).
  poscar  VASP POSCAR/CONTCAR -> P1 block (symmetry lost: warns; costs up to N_symop x more).

Basis: --basis-dir DIR with one file per element "<El>_<tag>.basis" (first line "Z NSHELL"; Z>200 = ECP),
       or --basisset NAME for the internal library (POB-TZVP-REV2, POB-DZVP-REV2, ...).

Usage:
  cry_input.py --geom ag2seo3.crygeo --basis-dir basis --basis-tag pob-TZVP-rev2 \
      --func HSE06 --mode kconv --kseries "2 1 2;3 2 2;4 2 3;5 3 4" --name hse_kconv
  cry_input.py --geom runs/hse_fullopt/fort.34 --basisset POB-TZVP-REV2 --func PBE \
      --mode atomopt --k 5 3 4 --name pbe_atomopt
"""
import argparse
import math
import re
import shutil
import sys
from pathlib import Path

SYMBOLS = ("X H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se "
           "Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy "
           "Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf "
           "Es Fm Md No Lr").split()
Z_OF = {s.lower(): i for i, s in enumerate(SYMBOLS)}

# functional -> DFT-block lines (GGA written as EXCHANGE/CORRELAT pairs; hybrids as standalone keywords)
FUNCS = {
    "PBE": ["EXCHANGE", "PBE", "CORRELAT", "PBE"],
    "PBESOL": ["EXCHANGE", "PBESOL", "CORRELAT", "PBESOL"],
    "BLYP": ["BLYP"],
    "B3LYP": ["B3LYP"], "B3PW": ["B3PW"], "PBE0": ["PBE0"], "PBESOL0": ["PBESOL0"],
    "HSE06": ["HSE06"], "HSESOL": ["HSESOL"], "PBE0-13": ["PBE0-13"],
}
HYBRIDS = {"B3LYP", "B3PW", "PBE0", "PBESOL0", "HSE06", "HSESOL", "PBE0-13"}


def elem(z):
    """Element symbol from a CRYSTAL conventional atomic number (Z>200 = ECP, Z mod 100)."""
    return SYMBOLS[z % 100 if z > 100 else z]


# space groups with a centred Bravais lattice (A/B/C/F/I/R): their SHRINK refers to the PRIMITIVE cell
CENTRED = set([5, 8, 9, 12, 15, 20, 21, 22, 23, 24] + list(range(35, 47)) + list(range(63, 75)) +
              [79, 80, 82, 87, 88, 97, 98, 107, 108, 109, 110, 119, 120, 121, 122, 139, 140, 141, 142,
               146, 148, 155, 160, 161, 166, 167, 196, 197, 199, 202, 203, 204, 206, 209, 210, 211,
               214, 216, 217, 219, 220, 225, 226, 227, 228, 229, 230])


def vectors_from_params(sg, par):
    """Cartesian lattice vectors (A) of a PRIMITIVE-lattice CRYSTAL block (standard settings)."""
    if sg <= 2:
        a, b, c, al, be, ga = par
    elif sg <= 15:
        a, b, c, be = par; al = ga = 90.0          # unique axis b
    elif sg <= 74:
        a, b, c = par; al = be = ga = 90.0
    elif sg <= 142:
        a, c = par; b = a; al = be = ga = 90.0
    elif sg <= 194:
        a, c = par; b = a; al = be = 90.0; ga = 120.0
    else:
        a = par[0]; b = c = a; al = be = ga = 90.0
    al, be, ga = map(math.radians, (al, be, ga))
    v1 = [a, 0.0, 0.0]
    v2 = [b * math.cos(ga), b * math.sin(ga), 0.0]
    cx = c * math.cos(be)
    cy = c * (math.cos(al) - math.cos(be) * math.cos(ga)) / math.sin(ga)
    return [v1, v2, [cx, cy, math.sqrt(c * c - cx * cx - cy * cy)]]


def recip_lengths(vec):
    """|b_i| in 1/A WITHOUT 2*pi (VASP Auto convention)."""
    import numpy as np
    B = np.linalg.inv(np.array(vec)).T
    return [float(np.linalg.norm(B[i])) for i in range(3)]


def primitive_vectors(args):
    """Primitive lattice vectors from fort.34 / POSCAR / crystal.out / P-lattice crygeo."""
    src = args.cell_from or args.geom
    name = Path(src).name
    if name.endswith(".out"):
        t = Path(src).read_text(errors="replace")
        i = t.rfind("DIRECT LATTICE VECTORS CARTESIAN COMPONENTS (ANGSTROM)")
        rows = t[i:].splitlines()[2:5]
        return [[float(x) for x in r.split()[:3]] for r in rows]
    if "fort.34" in name or name.endswith(".34"):
        L = Path(src).read_text().splitlines()
        return [[float(x) for x in L[i].split()[:3]] for i in (1, 2, 3)]
    if re.search(r"POSCAR|CONTCAR|\.vasp$", name):
        L = Path(src).read_text().splitlines()
        s = float(L[1].split()[0])
        return [[float(x) * s for x in L[i].split()[:3]] for i in (2, 3, 4)]
    lines, _ = read_crygeo(src)
    sgtok = lines[2].split()[0]
    if not sgtok.isdigit():
        sys.exit("--klengths with a crygeo needs the space group as a NUMBER (or use --cell-from)")
    sg = int(sgtok)
    if sg in CENTRED:
        sys.exit(f"space group {sg} is centred: SHRINK refers to the primitive cell. Give --cell-from "
                 "<crystal.out of any run of this structure | fort.34> (a TESTGEOM run takes seconds)")
    return vectors_from_params(sg, [float(x) for x in lines[3].split()])


def read_crygeo(path):
    lines = [l.rstrip() for l in Path(path).read_text().splitlines() if l.strip()]
    if lines[0].split()[0].upper() != "CRYSTAL":
        sys.exit("crygeo: first line must be CRYSTAL (3D only in this script)")
    nat = int(lines[4].split()[0])
    zs = [int(l.split()[0]) for l in lines[5:5 + nat]]
    if len(zs) != nat:
        sys.exit("crygeo: fewer atom lines than the declared count")
    return lines, zs


def read_fort34_z(path):
    lines = Path(path).read_text().split("\n")
    nsym = int(lines[4].split()[0])
    i = 5 + 4 * nsym
    nat = int(lines[i].split()[0])
    return [int(l.split()[0]) for l in lines[i + 1:i + 1 + nat]]


def read_poscar(path):
    L = Path(path).read_text().splitlines()
    s = float(L[1].split()[0])
    vec = [[float(x) * s for x in L[i].split()[:3]] for i in (2, 3, 4)]
    syms = L[5].split()
    cnts = [int(x) for x in L[6].split()]
    i = 7
    if L[i].strip()[0] in "sS":
        i += 1
    direct = L[i].strip()[0] in "dD"
    i += 1
    pos = [[float(x) for x in L[i + j].split()[:3]] for j in range(sum(cnts))]
    if not direct:  # cartesian -> fractional
        import numpy as np
        pos = (np.array(pos) * (s if s > 0 else 1.0)) @ np.linalg.inv(np.array(vec))
        pos = pos.tolist()
    norm = [math.sqrt(sum(c * c for c in v)) for v in vec]
    ang = lambda u, v: math.degrees(math.acos(sum(a * b for a, b in zip(u, v)) / (math.sqrt(sum(a * a for a in u)) * math.sqrt(sum(b * b for b in v)))))
    cell = norm + [ang(vec[1], vec[2]), ang(vec[0], vec[2]), ang(vec[0], vec[1])]
    species = [sy for sy, c in zip(syms, cnts) for _ in range(c)]
    return cell, species, pos


def basis_block(zs, args):
    """Return (lines, {element: conventional Z from basis file})."""
    out, zmap = [], {}
    for e in dict.fromkeys(elem(z) for z in zs):
        pat = f"{e}_{args.basis_tag}.basis" if args.basis_tag else f"{e}_*.basis"
        hits = sorted(Path(args.basis_dir).glob(pat))
        if len(hits) != 1:
            sys.exit(f"basis: expected exactly one file matching {args.basis_dir}/{pat}, found {len(hits)}")
        txt = hits[0].read_text().rstrip()
        zmap[e] = int(txt.split()[0])
        out.append(txt)
    return out + ["99 0", "END"], zmap


def opt_block(args):
    kind = {"fullopt": "FULLOPTG", "atomopt": "ATOMONLY"}[args.mode]
    b = ["OPTGEOM", kind, "TOLDEG", str(args.toldeg), "TOLDEX", str(args.toldex),
         "TOLDEE", str(args.opt_toldee), "MAXCYCLE", str(args.opt_maxcycle)]
    if args.extpress is not None and args.mode == "fullopt":
        b += ["EXTPRESS", str(args.extpress)]
    if args.restart_opt:
        b += ["RESTART"]
    return b + ["ENDOPT"]


def scf_block(args, k):
    func = args.func.upper()
    b = ["DFT"] + FUNCS[func] + (["SPIN"] if args.spin else []) + [args.grid, "ENDDFT"]
    if k[0] == k[1] == k[2]:
        b += ["SHRINK", f"{k[0]} {args.isp or 2 * k[0]}"]
    else:  # anisotropic net: IS=0; manual p.125: not compatible with SABF -> NOSYMADA
        b += ["SHRINK", f"0 {args.isp or 2 * k[0]}", f"{k[0]} {k[1]} {k[2]}", "NOSYMADA"]
    b += ["TOLINTEG", args.tolinteg, "TOLDEE", str(args.toldee), "FMIXING", str(args.fmixing),
          "MAXCYCLE", str(args.maxcycle), "BIPOSIZE", str(args.biposize), "EXCHSIZE", str(args.exchsize)]
    if args.spinlock:
        b += ["SPINLOCK", args.spinlock]
    if args.levshift:
        b += ["LEVSHIFT", args.levshift]
    if args.guessp:
        b += ["GUESSP"]
    if args.ppan:
        b += ["PPAN"]
    for f in args.extra3 or []:
        b += [l for l in Path(f).read_text().splitlines() if l.strip()]
    return b + ["END"]


def build(args, k, title):
    fmt = args.geom_fmt or ("fort34" if "fort.34" in Path(args.geom).name or args.geom.endswith(".34")
                            else "poscar" if re.search(r"POSCAR|CONTCAR|\.vasp$", Path(args.geom).name)
                            else "crygeo")
    if fmt == "crygeo":
        geo, zs = read_crygeo(args.geom)
    elif fmt == "fort34":
        geo, zs = ["EXTERNAL"], read_fort34_z(args.geom)
    else:
        cell, species, pos = read_poscar(args.geom)
        print("WARNING: POSCAR -> P1 block. Prefer a crygeo file with the real space group "
              "(cost scales ~ with the number of symmetry operators lost).", file=sys.stderr)
        geo, zs = None, [Z_OF[s.lower()] for s in species]
    if args.basisset:
        bas, zmap = ["BASISSET", args.basisset], {}
    else:
        bas, zmap = basis_block(zs, args)
    if fmt == "poscar":
        zconv = [zmap.get(elem(z), z) for z in zs]  # ECP flag (e.g. 247) taken from the basis file
        geo = ["CRYSTAL", "0 0 0", "1", " ".join(f"{x:.8f}" for x in cell), str(len(zs))]
        geo += [f"{z} {x % 1.0:.12f} {y % 1.0:.12f} {w % 1.0:.12f}" for z, (x, y, w) in zip(zconv, pos)]
    else:  # consistency: Z in geometry must equal the basis-file Z (ECP flag)
        for z in zs:
            if zmap and zmap[elem(z)] != z:
                sys.exit(f"Z mismatch: geometry uses {z} but basis file for {elem(z)} starts with {zmap[elem(z)]}")
    deck = [title] + geo
    if args.mode in ("fullopt", "atomopt"):
        deck += opt_block(args)
    if args.basisset:
        deck += bas                      # BASISSET replaces the END of block 1 and the whole block 2
    else:
        deck += ["END"] + bas
    deck += scf_block(args, k)
    return deck, fmt


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--geom", required=True)
    p.add_argument("--geom-fmt", choices=["crygeo", "fort34", "poscar"])
    p.add_argument("--name", required=True, help="run dir name under --root")
    p.add_argument("--root", default="runs")
    p.add_argument("--mode", required=True, choices=["kconv", "sp", "fullopt", "atomopt"])
    p.add_argument("--func", required=True, choices=sorted(FUNCS))
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--basis-dir")
    g.add_argument("--basisset", help="internal library name, e.g. POB-TZVP-REV2")
    p.add_argument("--basis-tag", help="file tag: <El>_<tag>.basis (default: unique <El>_*.basis)")
    p.add_argument("--k", type=int, nargs=3, help="Monkhorst-Pack shrinking factors IS1 IS2 IS3")
    p.add_argument("--kseries", help='kconv only: "a b c;a b c;..."')
    p.add_argument("--klengths", help='kconv only: VASP-Auto lengths "10 15 20 ..." (A): N_i = max(1, int(l*|b_i| + 0.5))')
    p.add_argument("--cell-from", help="crystal.out / fort.34 / POSCAR giving the primitive vectors for --klengths")
    p.add_argument("--kconv-opt", action="store_true", help="kconv: FULLOPTG in each mesh (VASP-rito parity; costly)")
    p.add_argument("--isp", type=int, help="Gilat net (default 2*IS1)")
    p.add_argument("--grid", default="XXLGRID", choices=["LGRID", "XLGRID", "XXLGRID", "XXXLGRID"])
    p.add_argument("--tolinteg", default="8 8 8 8 16")
    p.add_argument("--toldee", type=int, default=8, help="SCF: |dE| < 10^-N Ha")
    p.add_argument("--maxcycle", type=int, default=1500, help="SCF cycles (user rule: 1500)")
    p.add_argument("--fmixing", type=int, default=30)
    p.add_argument("--biposize", type=int, default=40000000)
    p.add_argument("--exchsize", type=int, default=40000000)
    p.add_argument("--toldeg", type=float, default=0.0003)
    p.add_argument("--toldex", type=float, default=0.0012)
    p.add_argument("--opt-toldee", type=int, default=8, help="OPTGEOM energy threshold (>= SCF TOLDEE)")
    p.add_argument("--opt-maxcycle", type=int, default=800, help="optimization steps (user rule: 800)")
    p.add_argument("--extpress", type=float, help="fullopt: hydrostatic pressure in Ha/bohr^3 (default none = 0)")
    p.add_argument("--restart-opt", action="store_true", help="add RESTART to OPTGEOM (needs OPTINFO.DAT + fort.9)")
    p.add_argument("--guessp", action="store_true", help="read density matrix from fort.20 (job copies fort.9)")
    p.add_argument("--spin", action="store_true", help="spin-polarized (SPIN in DFT block)")
    p.add_argument("--spinlock", help='"NALPHA-NBETA NCYCLES", e.g. "4 30"')
    p.add_argument("--levshift", help='"SHIFT_x0.1Ha LOCK", e.g. "5 1"')
    p.add_argument("--ppan", action="store_true", help="Mulliken population at the end")
    p.add_argument("--extra3", action="append", help="file with extra block-3 keywords (appended before END)")
    a = p.parse_args()

    if a.mode == "kconv":
        if a.klengths:
            bl = recip_lengths(primitive_vectors(a))
            meshes, names = [], []
            for l in a.klengths.split():
                m = tuple(max(1, int(float(l) * b + 0.5)) for b in bl)
                if m in meshes:
                    print(f"l={l}: mesh {m} repeats a shorter l, skipped", file=sys.stderr)
                    continue
                meshes.append(m)
                names.append(f"{a.name}_l{int(float(l)):02d}_k{m[0]}x{m[1]}x{m[2]}")
            print("|b_i| (1/A, no 2pi) =", " ".join(f"{b:.4f}" for b in bl), file=sys.stderr)
        elif a.kseries:
            meshes = [tuple(int(x) for x in s.split()) for s in a.kseries.split(";") if s.strip()]
            names = [f"{a.name}_k{m[0]}x{m[1]}x{m[2]}" for m in meshes]
        else:
            p.error("--mode kconv needs --kseries or --klengths")
        a.mode = "fullopt" if a.kconv_opt else "sp"
        mode_title = a.mode
    else:
        if not a.k:
            p.error("--k is required")
        meshes, names, mode_title = [tuple(a.k)], [a.name], a.mode
    for m, n in zip(meshes, names):
        d = Path(a.root) / n
        d.mkdir(parents=True, exist_ok=True)
        deck, fmt = build(a, m, f"{n} {a.func} {mode_title} k{m[0]}x{m[1]}x{m[2]}")
        (d / "INPUT").write_text("\n".join(deck) + "\n")
        if fmt == "fort34":
            shutil.copy(a.geom, d / "fort.34")
        if a.func.upper() in HYBRIDS and a.grid == "XXXLGRID":
            print("note: XXXLGRID with a hybrid is rarely worth the cost", file=sys.stderr)
        print("written", d / "INPUT")


if __name__ == "__main__":
    main()
