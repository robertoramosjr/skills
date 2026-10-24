#!/usr/bin/env python3
"""Plot the TURBOMOLE/Multiwfn spectra of a calculation folder, one figure per result.

Reads the broadened curves and stick files written by the extraction step
(uvvis_*.dat, ir_*.dat, dos_tdos.dat) and writes a separate single-panel figure
for each: <stem>_uvvis, <stem>_ir and <stem>_dos. Missing inputs are skipped
with a warning. When `vib_normal_modes`, `vibspectrum` and `coord` are present,
the five most intense IR peaks are labelled with the dominant character of the
calculated normal mode (see ir_mode_labels.py).

Each figure is an EPS vector master (the submission file) plus a 300 dpi PNG
preview, following the academic-figure-skill rules: serif type, closed frame,
legend inside the frame.

Usage:
    python plot_spectra.py                                # run from the calculation folder
    python plot_spectra.py --dir spectra --output fig_ni  # fig_ni_uvvis/_ir/_dos .eps/.png
    python plot_spectra.py --only ir --width double       # one figure, 183 mm wide
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ir_mode_labels  # noqa: E402

# Typography and export baseline, from academic-figure-skill/references/typography.md
# and export-specs.md. Serif per the user's rule (Times New Roman); STIXGeneral is the
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
HEIGHT_RATIO = 0.75
PREVIEW_DPI = 300

# Colour-blind-safe set (Okabe-Ito). Solid colours only: alpha in an EPS
# forces a raster block into the vector master, so the DOS fill is opaque.
CURVE_COLOR = "#0072B2"
STICK_COLOR = "#D55E00"
DOS_COLOR = "#009E73"
DOS_FILL = "#CCE8DF"
LABEL_FONTSIZE = 6.5
LABEL_WINDOW_CM = 80  # labels start above the highest curve point within this window


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dir", default=".", type=Path,
                        help="folder holding the .dat files (default: current directory)")
    parser.add_argument("--output", default="spectra", type=str,
                        help="output stem; writes <stem>_<result>.eps/.png (default: spectra)")
    parser.add_argument("--width", choices=sorted(WIDTH_MM), default="single",
                        help="journal column width (default: single, 89 mm)")
    parser.add_argument("--only", choices=("uvvis", "ir", "raman", "dos"), default=None,
                        help="plot only this result (default: all four)")
    parser.add_argument("--ir-labels", default=5, type=int,
                        help="number of IR/Raman peaks labelled with the mode character; 0 disables (default: 5)")
    return parser.parse_args(argv)


def load_xy(path, columns=(0, 1)):
    """Load two numeric columns, ignoring comment lines starting with '#'."""
    data = np.loadtxt(path, comments="#", usecols=columns, ndmin=2)
    return data[:, 0], data[:, 1]


def headroom(ax, factor):
    """Raise the y-limit so the legend and labels sit in empty space, not on the data."""
    ax.set_ylim(0, ax.get_ylim()[1] * factor)


def plot_uvvis(ax, folder, **_):
    """UV-vis: broadened curve in nm with oscillator-strength sticks."""
    broad = folder / "uvvis_broadened.dat"
    sticks = folder / "uvvis_sticks.dat"
    if not broad.exists() and not sticks.exists():
        return False
    if broad.exists():
        x, y = load_xy(broad, columns=(0, 2))
        ax.plot(x, y, color=CURVE_COLOR, lw=1.0, label="broadened")
    if sticks.exists():
        wl, _, f = np.loadtxt(sticks, comments="#", unpack=True)
        ax.vlines(wl, 0, f, color=STICK_COLOR, lw=0.8, label="sticks")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Oscillator strength (a.u.)")
    headroom(ax, 1.3)
    ax.legend(loc="upper right")
    return True


def label_ir_peaks(ax, folder, curve_x, curve_y, top_n):
    """Vertical mode-character labels above the top_n most intense IR peaks."""
    needed = ("coord", "vib_normal_modes", "vibspectrum")
    absent = [name for name in needed if not (folder / name).exists()]
    if absent:
        print(f"warning: IR labels skipped, missing {', '.join(absent)} in {folder}", file=sys.stderr)
        return
    ymax = curve_y.max()
    ax.set_ylim(0, ymax * 1.45)
    for wn, _, text in ir_mode_labels.peak_labels(folder, top_n=top_n):
        near = np.abs(curve_x - wn) <= LABEL_WINDOW_CM
        y0 = curve_y[near].max() + 0.02 * ymax
        ax.text(wn, y0, text, rotation=90, ha="center", va="bottom",
                fontsize=LABEL_FONTSIZE, color="0.15")


def plot_ir(ax, folder, ir_labels=5, **_):
    """IR: broadened spectrum with intensity sticks and mode labels on the main peaks."""
    broad = folder / "ir_broadened.dat"
    sticks = folder / "ir_sticks.dat"
    if not broad.exists() and not sticks.exists():
        return False
    curve = None
    if broad.exists():
        curve = load_xy(broad)
        ax.plot(*curve, color=CURVE_COLOR, lw=1.0, label="broadened")
    if sticks.exists():
        nu, inten = load_xy(sticks)
        ax.vlines(nu, 0, inten, color=STICK_COLOR, lw=0.8, label="sticks")
    ax.set_xlabel(r"Wavenumber (cm$^{-1}$)")
    ax.set_ylabel(r"IR intensity (km mol$^{-1}$)")
    headroom(ax, 1.3)
    if curve is not None and ir_labels > 0:
        label_ir_peaks(ax, folder, curve[0], curve[1], ir_labels)
    ax.legend(loc="upper right")
    return True


def plot_dos(ax, folder, **_):
    """Total DOS from Multiwfn, energy in eV."""
    tdos = folder / "dos_tdos.dat"
    if not tdos.exists():
        return False
    e, y = load_xy(tdos)
    ax.plot(e, y, color=DOS_COLOR, lw=1.0)
    ax.fill_between(e, 0, y, color=DOS_FILL, lw=0)
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel("TDOS (arb. units)")
    return True


BOHR2_TO_A2 = 0.28002852  # 1 bohr^2 in angstrom^2
RAMAN_FWHM_CM = 20.0  # same Lorentzian width as the IR curve
RAMAN_MIN_CM = 100.0  # below this the 1/nu prefactor and the notch filters dominate; modes omitted


def read_raman(path):
    """Rows of `raman_spectrum.dat` (control `$raman spectrum`, from intense) with
    the selection rule YES: (mode, wavenumber, sigma) with the unpolarised 90 degree
    cross section in A^2/sr. The file lists T,T (incident and scattered field
    orthogonal to the scattering plane) and II,II (parallel); (par,ort) and (ort,par)
    equal II,II (intense.out), so unpolarised incident light summed over the scattered
    polarisations is (TT + 3 II)/2."""
    rows = []
    for line in Path(path).read_text().splitlines():
        parts = line.replace("D", "E").split()
        if line.startswith(("#", "$")) or len(parts) != 8 or parts[3] != "YES":
            continue
        tt, ii = float(parts[6]), float(parts[7])
        rows.append((int(parts[0]), float(parts[2]), 0.5 * (tt + 3.0 * ii) * BOHR2_TO_A2))
    return rows


def plot_raman(ax, folder, ir_labels=5, **_):
    """Raman: Lorentzian-broadened differential cross section with sticks and mode labels."""
    path = folder / "raman_spectrum.dat"
    if not path.exists():
        return False
    rows = [r for r in read_raman(path) if r[1] >= RAMAN_MIN_CM]
    modes, nu, sigma = (np.array(col) for col in zip(*rows))
    exponent = int(np.floor(np.log10(sigma.max())))
    scale = 10.0 ** exponent
    grid = np.arange(RAMAN_MIN_CM, 4000.0 + 1.0)
    half = RAMAN_FWHM_CM / 2.0
    curve = (sigma[None, :] / scale * half**2 / ((grid[:, None] - nu[None, :]) ** 2 + half**2)).sum(axis=1)
    ax.plot(grid, curve, color=CURVE_COLOR, lw=1.0, label="broadened")
    ax.vlines(nu, 0, sigma / scale, color=STICK_COLOR, lw=0.8, label="sticks")
    ax.set_xlabel(r"Wavenumber (cm$^{-1}$)")
    ax.set_ylabel(rf"Raman cross section (10$^{{{exponent}}}$ Å$^2$ sr$^{{-1}}$)")
    ax.text(1.0, 1.015, r"514.5 nm, 298.15 K, 90°, unpolarised; modes < 100 cm$^{-1}$ omitted", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=LABEL_FONTSIZE)
    ax.set_xlim(RAMAN_MIN_CM - 100.0, 4000.0)
    headroom(ax, 1.3)
    if ir_labels > 0:
        needed = ("coord", "vib_normal_modes")
        absent = [name for name in needed if not (folder / name).exists()]
        if absent:
            print(f"warning: Raman labels skipped, missing {', '.join(absent)} in {folder}", file=sys.stderr)
        else:
            ymax = curve.max()
            ax.set_ylim(0, ymax * 1.45)
            ranking = list(zip(modes.tolist(), nu.tolist(), sigma.tolist()))
            for wn, _, text in ir_mode_labels.peak_labels(folder, top_n=ir_labels, spec=ranking):
                near = np.abs(grid - wn) <= LABEL_WINDOW_CM
                ax.text(wn, curve[near].max() + 0.02 * ymax, text, rotation=90, ha="center",
                        va="bottom", fontsize=LABEL_FONTSIZE, color="0.15")
    ax.legend(loc="upper right")
    return True


PLOTTERS = {"uvvis": plot_uvvis, "ir": plot_ir, "raman": plot_raman, "dos": plot_dos}


def save_figure(fig, stem):
    """EPS vector master plus a 300 dpi PNG preview."""
    eps_path = stem.with_suffix(".eps")
    png_path = stem.with_suffix(".png")
    fig.savefig(eps_path, format="eps")
    fig.savefig(png_path, dpi=PREVIEW_DPI)
    print(f"wrote {eps_path.resolve()} (vector master)")
    print(f"wrote {png_path.resolve()} (preview)")


def main(argv=None):
    args = parse_args(argv)
    folder = args.dir.resolve()
    plt.rcParams.update(BASE_RC)
    width = WIDTH_MM[args.width] / 25.4

    names = [args.only] if args.only else list(PLOTTERS)
    for name in names:
        fig, ax = plt.subplots(figsize=(width, width * HEIGHT_RATIO), constrained_layout=True)
        if PLOTTERS[name](ax, folder, ir_labels=args.ir_labels):
            save_figure(fig, Path(f"{args.output}_{name}"))
        else:
            print(f"warning: no {name} data found in {folder}, figure skipped", file=sys.stderr)
        plt.close(fig)


if __name__ == "__main__":
    main()
