#!/usr/bin/env python3
"""Label IR peaks with the dominant character of the calculated normal mode.

Reads `coord`, `vib_normal_modes` and `vibspectrum` from a TURBOMOLE aoforce
folder and decomposes the kinetic energy of each normal mode over atom roles
found from the bond graph, so it works for metal complexes (unlike the azo-dye
script in academic-figure-skill). Roles:
    H on C/N/O   -> nu(X-H) along the bond; delta(X-H) in plane; gamma(X-H) out of plane
    metal        -> nu(M-L)
    donor atom   -> stretch along its bond to the nearest non-metal heavy atom
                    (e.g. nu(C=N), nu(C-O)); the rest of its motion -> nu(M-L)
    N-N pair     -> nu(N-N) along the N-N axis
    other heavy  -> ring ip (in plane) / ring oop (out of plane)
The label is the dominant class (plus the second if >= 22 %). It is a dominant
character label, not a full potential energy distribution (PED).

Usage:
    python ir_mode_labels.py --folder <aoforce_folder> --top 5
    python ir_mode_labels.py --folder . --table          # all modes above --min-rel
"""

import argparse
import itertools
import re
from pathlib import Path

import numpy as np

MASS = {"h": 1.008, "c": 12.011, "n": 14.007, "o": 15.999, "s": 32.06, "p": 30.974,
        "f": 18.998, "cl": 35.45, "br": 79.904, "fe": 55.845, "co": 58.933,
        "ni": 58.693, "cu": 63.546, "zn": 65.38}
COV = {"h": 0.31, "c": 0.76, "n": 0.71, "o": 0.66, "s": 1.05, "p": 1.07, "f": 0.57,
       "cl": 1.02, "br": 1.20, "fe": 1.32, "co": 1.26, "ni": 1.24, "cu": 1.32, "zn": 1.22}
METALS = {"fe", "co", "ni", "cu", "zn"}
BOHR = 0.529177210903
SECOND = 0.22  # minimum share of the second class to enter the label
CHAR_PRETTY = {"nu(X-H)": "ν(X–H)", "delta(X-H)": "δ(X–H)", "gamma(X-H)": "γ(X–H)",
               "nu(M-L)": "ν(M–L)", "nu(N-N)": "ν(N–N)", "ring ip": "ring ip",
               "ring oop": "ring oop"}


def read_coord(path):
    """Return (elements, xyz in angstrom) from a TURBOMOLE coord file."""
    el, xyz = [], []
    block = Path(path).read_text().split("$coord")[1].split("$")[0].strip().splitlines()
    for line in block:
        parts = line.split()
        xyz.append([float(v) for v in parts[:3]])
        el.append(parts[3].lower())
    return el, np.array(xyz) * BOHR


def read_modes(path, n_atoms):
    """Return L (3N, nmodes), column k = normal mode k (Cartesian displacements, unit
    Euclidean norm, orthogonal in the mass metric). Lines are fixed width: Cartesian
    component in columns 1-3, block of five modes in columns 4-5, then up to five
    values. The fields touch once the block number reaches 10 (e.g. '  110'), so a
    whitespace split loses those lines."""
    ncomp = 3 * n_atoms
    cells = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith("$") or not line.strip():
            continue
        row, block = int(line[:3]), int(line[3:5])
        vals = [float(x.replace("D", "E")) for x in line[5:].split()]
        for offset, v in enumerate(vals):
            cells[(row - 1, 5 * (block - 1) + offset)] = v
    nmodes = max(col for _, col in cells) + 1
    L = np.zeros((ncomp, nmodes))
    for (row, col), v in cells.items():
        L[row, col] = v
    return L


def read_vibspectrum(path):
    """Return [(mode, wavenumber, ir_intensity)] from a vibspectrum file."""
    out = []
    for line in Path(path).read_text().splitlines():
        if line.startswith(("$", "#")) or not line.strip():
            continue
        parts = line.split()
        nums = [p for p in parts[1:] if re.fullmatch(r"-?\d+\.\d+", p)]
        if len(nums) >= 2:
            out.append((int(parts[0]), float(nums[0]), float(nums[1])))
    return out


def neighbors(el, xyz):
    """Bond graph: list of (neighbour index, distance) per atom."""
    nb = [[] for _ in el]
    for i, j in itertools.combinations(range(len(el)), 2):
        d = np.linalg.norm(xyz[i] - xyz[j])
        if d < 1.25 * (COV[el[i]] + COV[el[j]]) and not (el[i] == "h" and el[j] == "h"):
            nb[i].append((j, d))
            nb[j].append((i, d))
    return nb


def local_normal(i, xyz, nb):
    """Normal of the plane defined by the two nearest neighbours of atom i."""
    near = sorted(nb[i], key=lambda t: t[1])
    if len(near) < 2:
        return None
    u1, u2 = xyz[near[0][0]] - xyz[i], xyz[near[1][0]] - xyz[i]
    n = np.cross(u1, u2)
    norm = np.linalg.norm(n)
    return n / norm if norm > 1e-6 else None


def unit(v):
    return v / np.linalg.norm(v)


def donor_axis_label(i, el, xyz, nb):
    """For an atom bonded to a metal: (partner index, stretch axis, label) towards its
    nearest non-metal heavy neighbour, or (None, None, None). C=N / C=O style bonds
    are named by length so the label tells the bond order apart."""
    heavy = [(j, d) for j, d in nb[i] if el[j] not in METALS and el[j] != "h"]
    if not heavy:
        return None, None, None
    j, d = min(heavy, key=lambda t: t[1])
    pair = "".join(sorted((el[i].upper(), el[j].upper())))
    short = {"CN": 1.33, "CO": 1.25, "CS": 1.70}.get(pair)
    sym = "=" if short is not None and d < short else "–"
    names = sorted((el[i].upper(), el[j].upper()), key=lambda s: "CNOSP".find(s))
    return j, unit(xyz[j] - xyz[i]), f"nu({names[0]}{sym}{names[1]})"


def decompose(folder):
    """Return per-mode class fractions: {mode: {class: fraction}} and the class list."""
    folder = Path(folder)
    el, xyz = read_coord(folder / "coord")
    n = len(el)
    L = read_modes(folder / "vib_normal_modes", n)
    nb = neighbors(el, xyz)
    mass = np.array([MASS[e] for e in el])

    normals = [local_normal(i, xyz, nb) for i in range(n)]
    for i in range(n):
        if el[i] == "h" and nb[i]:
            normals[i] = normals[nb[i][0][0]]
    bonded_to_metal = [any(el[j] in METALS for j, _ in nb[i]) for i in range(n)]
    donor = {i: donor_axis_label(i, el, xyz, nb) for i in range(n) if bonded_to_metal[i]}
    # The partner atom of a donor bond carries the other half of that stretch.
    partner = {}
    for i, (j, axis, name) in donor.items():
        if j is not None and j not in donor and j not in partner:
            partner[j] = (axis, name)
    nn_axis = {}
    for i in range(n):
        for j, _ in nb[i]:
            if j > i and el[i] == "n" and el[j] == "n":
                axis = unit(xyz[j] - xyz[i])
                nn_axis[i] = nn_axis[j] = axis

    classes, result = set(), {}
    for k in range(L.shape[1]):
        disp = L[:, k].reshape(n, 3)
        frac = {}

        def add(name, value):
            frac[name] = frac.get(name, 0.0) + value
            classes.add(name)

        for i in range(n):
            d = disp[i]
            w = mass[i]
            tot = float(d @ d)
            nrm = normals[i]
            oop = float((d @ nrm) ** 2) if nrm is not None else 0.0
            if el[i] == "h" and nb[i]:
                par = float((d @ unit(xyz[i] - xyz[nb[i][0][0]])) ** 2)
                add("nu(X-H)", w * par)
                add("gamma(X-H)", w * oop)
                add("delta(X-H)", w * max(tot - par - oop, 0.0))
            elif el[i] in METALS:
                add("nu(M-L)", w * tot)
            elif i in donor and donor[i][0] is not None:
                _, axis, name = donor[i]
                par = float((d @ axis) ** 2)
                add(name, w * par)
                add("nu(M-L)", w * (tot - par))
            elif i in partner:
                axis, name = partner[i]
                par = float((d @ axis) ** 2)
                add(name, w * par)
                add("ring oop", w * oop)
                add("ring ip", w * max(tot - par - oop, 0.0))
            elif i in nn_axis:
                par = float((d @ nn_axis[i]) ** 2)
                add("nu(N-N)", w * par)
                add("ring oop", w * oop)
                add("ring ip", w * max(tot - par - oop, 0.0))
            else:
                add("ring oop", w * oop)
                add("ring ip", w * max(tot - oop, 0.0))
        total = sum(frac.values())
        result[k + 1] = {c: v / total for c, v in frac.items()} if total > 0 else {}
    return result


def pretty(name):
    """Display form of a class name (greek letters, en dash)."""
    if name in CHAR_PRETTY:
        return CHAR_PRETTY[name]
    return name.replace("nu(", "ν(").replace("delta(", "δ(").replace("gamma(", "γ(")


def mode_label(fractions, max_cats=1):
    """Dominant class, plus the second if its share is >= SECOND and max_cats > 1."""
    ranked = sorted(fractions.items(), key=lambda t: -t[1])
    label = pretty(ranked[0][0])
    if max_cats > 1 and len(ranked) > 1 and ranked[1][1] >= SECOND:
        label += " + " + pretty(ranked[1][0])
    return label


def peak_labels(folder, top_n=5, merge=100.0, max_cats=1):
    """Labels for the `top_n` most intense IR peaks: [(wavenumber, intensity, text)],
    ordered by wavenumber. Greedy by intensity; a peak closer than `merge` cm-1 to an
    already chosen one is skipped so the vertical labels do not collide."""
    fractions = decompose(folder)
    spec = read_vibspectrum(Path(folder) / "vibspectrum")
    chosen = []
    for mode, wn, inten in sorted(spec, key=lambda t: -t[2]):
        if wn < 20 or mode not in fractions:
            continue
        if len(chosen) >= top_n:
            break
        if all(abs(wn - c[0]) >= merge for c in chosen):
            chosen.append((wn, inten, mode))
    return [(wn, inten, mode_label(fractions[mode], max_cats)) for wn, inten, mode in sorted(chosen)]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--folder", default=".", type=Path,
                        help="folder with coord, vib_normal_modes, vibspectrum (default: .)")
    parser.add_argument("--top", default=5, type=int, help="number of labelled peaks (default: 5)")
    parser.add_argument("--merge", default=100.0, type=float,
                        help="minimum spacing between labelled peaks, cm-1 (default: 100)")
    parser.add_argument("--table", action="store_true",
                        help="print every mode above --min-rel of the strongest intensity")
    parser.add_argument("--min-rel", default=0.12, type=float,
                        help="relative intensity cut for --table (default: 0.12)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.table:
        fractions = decompose(args.folder)
        spec = read_vibspectrum(args.folder / "vibspectrum")
        top = max(i for _, _, i in spec)
        print(f"{'mode':>4} {'cm-1':>8} {'km/mol':>8}  label (class shares)")
        for mode, wn, inten in spec:
            if inten >= args.min_rel * top:
                ranked = sorted(fractions[mode].items(), key=lambda t: -t[1])[:3]
                shares = "  ".join(f"{pretty(c)}={v:.2f}" for c, v in ranked)
                print(f"{mode:4d} {wn:8.1f} {inten:8.1f}  {mode_label(fractions[mode], 2):28s} {shares}")
    else:
        for wn, inten, text in peak_labels(args.folder, args.top, args.merge):
            print(f"{wn:8.1f} cm-1  {inten:8.1f} km/mol  {text}")


if __name__ == "__main__":
    main()
