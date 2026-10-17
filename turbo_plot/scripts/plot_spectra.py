#!/usr/bin/env python3
"""Plot the TURBOMOLE/Multiwfn spectra found in a calculation folder for publication.

Reads the broadened curves and stick files written by the extraction step
(uvvis_*.dat, ir_*.dat, dos_tdos.dat) and writes one three-panel figure:
UV-vis (sticks + broadened), IR (sticks + broadened) and total DOS.
Missing inputs are skipped with a warning, so a partial folder still plots.

Output is an EPS vector master (the submission file) plus a 300 dpi PNG
preview, following the academic-figure-skill rules: serif type, closed frame,
panel labels a) b) c), legend inside the frame.

Usage:
    python plot_spectra.py                              # run from the calculation folder
    python plot_spectra.py --dir spectra --output fig1  # writes fig1.eps and fig1.png
    python plot_spectra.py --width single               # 89 mm column instead of 183 mm
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# Typography and export baseline, from academic-figure-skill/references/typography.md
# and export-specs.md. Serif per the user's rule (Times New Roman); STIX is the
# fallback because it ships with matplotlib and has Times metrics.
BASE_RC = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "Liberation Serif", "Nimbus Roman", "STIXGeneral"],
    "mathtext.fontset": "stix",
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.spines.top": True,
    "axes.spines.right": True,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.bbox": "tight",
}

WIDTH_MM = {"single": 89, "double": 183}
HEIGHT_MM = 70
PREVIEW_DPI = 300

# Colour-blind-safe pair (Okabe-Ito). Solid colours only: alpha in an EPS
# forces a raster block into the vector master, so the DOS fill is opaque.
CURVE_COLOR = "#0072B2"
STICK_COLOR = "#D55E00"
DOS_COLOR = "#009E73"
DOS_FILL = "#CCE8DF"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dir", default=".", type=Path,
                        help="folder holding the .dat files (default: current directory)")
    parser.add_argument("--output", default="spectra", type=str,
                        help="output stem; writes <stem>.eps and <stem>.png (default: spectra)")
    parser.add_argument("--width", choices=sorted(WIDTH_MM), default="double",
                        help="journal column width (default: double, 183 mm)")
    return parser.parse_args(argv)


def load_xy(path, columns=(0, 1)):
    """Load two numeric columns, ignoring comment lines starting with '#'."""
    data = np.loadtxt(path, comments="#", usecols=columns, ndmin=2)
    return data[:, 0], data[:, 1]


def panel_label(ax, letter):
    """Panel label in the a) format, bold, outside the top-left corner of the frame."""
    ax.text(-0.16, 1.04, f"{letter})", transform=ax.transAxes,
            fontweight="bold", fontsize=8, ha="left", va="bottom")


def headroom(ax, factor=1.3):
    """Raise the y-limit so the legend sits in empty space instead of on the data."""
    ax.set_ylim(0, ax.get_ylim()[1] * factor)


def plot_uvvis(ax, folder):
    """UV-vis: broadened curve in nm with oscillator-strength sticks."""
    broad = folder / "uvvis_broadened.dat"
    sticks = folder / "uvvis_sticks.dat"
    if broad.exists():
        x, y = load_xy(broad, columns=(0, 2))
        ax.plot(x, y, color=CURVE_COLOR, lw=1.0, label="broadened")
    if sticks.exists():
        wl, _, f = np.loadtxt(sticks, comments="#", unpack=True)
        ax.vlines(wl, 0, f, color=STICK_COLOR, lw=0.8, label="sticks")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Oscillator strength (a.u.)")
    headroom(ax)
    ax.legend(loc="upper right")


def plot_ir(ax, folder):
    """IR: broadened spectrum with intensity sticks."""
    broad = folder / "ir_broadened.dat"
    sticks = folder / "ir_sticks.dat"
    if broad.exists():
        x, y = load_xy(broad)
        ax.plot(x, y, color=CURVE_COLOR, lw=1.0, label="broadened")
    if sticks.exists():
        nu, inten = load_xy(sticks)
        ax.vlines(nu, 0, inten, color=STICK_COLOR, lw=0.8, label="sticks")
    ax.set_xlabel(r"Wavenumber (cm$^{-1}$)")
    ax.set_ylabel(r"IR intensity (km mol$^{-1}$)")
    headroom(ax)
    ax.legend(loc="upper right")


def plot_dos(ax, folder):
    """Total DOS from Multiwfn, energy in eV."""
    tdos = folder / "dos_tdos.dat"
    if tdos.exists():
        e, y = load_xy(tdos)
        ax.plot(e, y, color=DOS_COLOR, lw=1.0)
        ax.fill_between(e, 0, y, color=DOS_FILL, lw=0)
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel("TDOS (arb. units)")


def main(argv=None):
    args = parse_args(argv)
    folder = args.dir.resolve()

    missing = [name for name in ("uvvis_broadened.dat", "ir_broadened.dat", "dos_tdos.dat")
               if not (folder / name).exists()]
    for name in missing:
        print(f"warning: {name} not found in {folder}", file=sys.stderr)

    plt.rcParams.update(BASE_RC)
    width = WIDTH_MM[args.width] / 25.4
    height = HEIGHT_MM / 25.4
    fig, axes = plt.subplots(1, 3, figsize=(width, height), constrained_layout=True)

    plot_uvvis(axes[0], folder)
    plot_ir(axes[1], folder)
    plot_dos(axes[2], folder)
    for ax, letter in zip(axes, "abc"):
        panel_label(ax, letter)

    stem = Path(args.output)
    eps_path = stem.with_suffix(".eps")
    png_path = stem.with_suffix(".png")
    fig.savefig(eps_path, format="eps")
    fig.savefig(png_path, dpi=PREVIEW_DPI)
    print(f"wrote {eps_path.resolve()} (vector master)")
    print(f"wrote {png_path.resolve()} (preview)")


if __name__ == "__main__":
    main()
