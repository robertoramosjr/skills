#!/usr/bin/env python3
"""Plot a Multiwfn PDOS export (DOS_curve.txt) as one publication figure.

Reads the fixed-width DOS_curve.txt written by Multiwfn menu 10 -> 3, with
N fragments defined in the `-1 Define fragments` menu (SCPA, element or
element x angular momentum). Columns: energy (a.u.) | TDOS | OPDOS(1,2) |
fragment 1..10 (no OPDOS column with Becke: use --no-opdos). Multiwfn glues columns when a value is negative, so the file is
read by field width, never with split(). The curves are converted to eV, written
as a plain dataset (<output>.dat) and drawn as an EPS vector master plus a
300 dpi PNG preview, same style as plot_spectra.py.

Usage:
    python plot_pdos.py --curve curve_elem.txt --labels Ni S N O C H \\
        --orginfo ../orginfo.txt --output pdos_elements
    python plot_pdos.py --curve curve_ni.txt --labels "Ni 4s" "Ni 4p" "Ni 3d" "Ni f" \\
        --no-tdos --ylabel "Ni PDOS (arb. units)" --output pdos_ni_angular
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_spectra import BASE_RC, HEIGHT_RATIO, WIDTH_MM, headroom, save_figure  # noqa: E402

HARTREE_TO_EV = 27.211386245988
# Okabe-Ito; solid colours only (no alpha, so the EPS stays vector).
PALETTE = ["#D55E00", "#E69F00", "#0072B2", "#56B4E9", "#222222", "#CC79A7", "#009E73", "#8C6D31"]
TDOS_FILL = "#E3E3E3"
TDOS_EDGE = "#7A7A7A"


def read_curve(path):
    """Fixed-width read: energy in 10 chars, then 12-char fields. Returns an array in eV."""
    rows = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        row = [float(line[:10])]
        row += [float(line[10 + 12 * k:22 + 12 * k]) for k in range((len(line) - 10) // 12)]
        rows.append(row)
    data = np.array(rows)
    data[:, 0] *= HARTREE_TO_EV
    return data


def homo_lumo(orginfo, au=False):
    """HOMO and LUMO (eV) from Multiwfn orginfo.txt: highest occupied / lowest empty level.
    au=True when the file holds energies in hartree (converted to eV)."""
    levels = []
    for line in Path(orginfo).read_text().splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            levels.append((float(parts[0]), float(parts[1])))
    occ = [e for e, n in levels if n > 0.5]
    emp = [e for e, n in levels if n <= 0.5]
    scale = 27.211386 if au else 1.0
    return max(occ) * scale, min(emp) * scale


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--curve", required=True, type=Path, help="Multiwfn DOS_curve.txt")
    p.add_argument("--labels", required=True, nargs="+",
                   help="fragment names in the order defined in Multiwfn")
    p.add_argument("--output", required=True, help="output stem (.eps, .png, .dat)")
    p.add_argument("--orginfo", type=Path, help="orginfo.txt, to mark the HOMO")
    p.add_argument("--orginfo-au", action="store_true",
                   help="orginfo.txt energies are in hartree (sanity: HOMO of ~-0.2 means a.u.)")
    p.add_argument("--width", choices=sorted(WIDTH_MM), default="single")
    p.add_argument("--xlim", nargs=2, type=float, default=[-20.0, 2.0], metavar=("EMIN", "EMAX"))
    p.add_argument("--no-opdos", action="store_true",
                   help="curve has no OPDOS column (Becke/Hirshfeld; SCPA/Mulliken with >=2 fragments do)")
    p.add_argument("--normalize", action="store_true",
                   help="rescale fragments point by point so they sum to the TDOS (Becke: the numerical "
                        "integration leaves 1-35 %% of the density unassigned)")
    p.add_argument("--no-tdos", action="store_true", help="omit the TDOS background")
    p.add_argument("--ylabel", default="DOS (arb. units)")
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    data = read_curve(a.curve)
    n = len(a.labels)
    energy, tdos, frags = data[:, 0], data[:, 1], data[:, (2 if a.no_opdos else 3):(2 if a.no_opdos else 3) + n]

    if a.normalize:
        total = frags.sum(axis=1)
        frags = frags * np.divide(tdos, total, out=np.zeros_like(tdos), where=total > 0)[:, None]

    header = "energy_eV TDOS " + " ".join(l.replace(" ", "_") for l in a.labels)
    np.savetxt(f"{a.output}.dat", np.column_stack([energy, tdos, frags]), fmt="%.6g", header=header)
    print(f"wrote {Path(a.output + '.dat').resolve()}")

    plt.rcParams.update(BASE_RC)
    width = WIDTH_MM[a.width] / 25.4
    fig, ax = plt.subplots(figsize=(width, width * HEIGHT_RATIO), constrained_layout=True)
    if not a.no_tdos:
        ax.fill_between(energy, 0, tdos, color=TDOS_FILL, lw=0, label="TDOS")
        ax.plot(energy, tdos, color=TDOS_EDGE, lw=0.5)
    for k, label in enumerate(a.labels):
        ax.plot(energy, frags[:, k], color=PALETTE[k % len(PALETTE)], lw=0.9, label=label)
    if a.orginfo:
        homo, lumo = homo_lumo(a.orginfo, a.orginfo_au)
        ax.axvline(homo, color="#000000", ls="--", lw=0.6, label=f"HOMO ({homo:.2f} eV)")
        ax.axvline(lumo, color="#000000", ls=":", lw=0.6, label=f"LUMO ({lumo:.2f} eV)")
    ax.set_xlim(*a.xlim)
    ymax = max(tdos[(energy > a.xlim[0]) & (energy < a.xlim[1])].max() if not a.no_tdos else 0,
               frags[(energy > a.xlim[0]) & (energy < a.xlim[1])].max())
    ax.set_ylim(0, ymax)
    headroom(ax, 1.45)
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel(a.ylabel)
    ax.legend(loc="upper left", ncol=2 if len(a.labels) + (not a.no_tdos) > 4 else 1,
              handlelength=1.4, columnspacing=1.0, borderaxespad=0.4)
    save_figure(fig, Path(a.output))
    plt.close(fig)


if __name__ == "__main__":
    main()
