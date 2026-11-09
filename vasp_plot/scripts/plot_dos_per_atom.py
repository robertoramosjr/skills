#!/usr/bin/env python3
"""Spin-polarized TDOS + element PDOS normalized per atom, read directly from DOSCAR (+ CONTCAR/POSCAR species).

Normalization (rule of the user, 2026-11-07, same as turbo_plot/academic-figure-skill DOS figures):
  TDOS  -> states/eV per atom of the cell (divided by N_cell), drawn as a light solid grey fill (no alpha);
  PDOS  -> states/eV per atom of each species (sum over that species / N_species), drawn as lines.
Per-atom units make cells of different sizes (112 vs 222 atoms) and a single dopant directly comparable.

Majority spin is plotted positive. ':auto' flips when the integrated magnetization at E_F is negative; ':flip' forces it,
for instance when the dopant majority sits in the VASP spin-down channel
(e.g. Ag2CrO4 Ag_T_N_OK, total M = -3 muB). Energies are E - E_F, with E_F from the DOSCAR header (line 6).
Display broadening: Gaussian of standard deviation --sigma (default 0.1 eV, as dos_analysis.py, which made the
old DOS_raw_data.csv); the raw DOSCAR (ISMEAR=0, SIGMA=0.01) is too spiky to read at print size. Integrals are kept.
Total-DOS scale check: the integrated TDOS at E_F must equal NELECT (OUTCAR). Six 222-atom DOSCARs of Ag2CrO4
(VASP 6.6.0 build Apr 08 2026) have the TDOS block divided by exactly 800 (vasprun.xml is right, PDOS is right);
the script rescales by NELECT/integral when they differ by >2 % and prints a warning.
Works for LORBIT=10 or 11 (up = even columns, down = odd columns of each atom block); an ISPIN=1 DOSCAR
(non-magnetic reference, e.g. the pristine host) is drawn with half of each density in each channel.

Usage:
  plot_dos_per_atom.py --panel DIR:LABEL[:flip] [--panel ...] --out PREFIX [--xlim -4 4] [--ylim -11 11]
                       [--width single|double] [--csv]
One panel per --panel, stacked vertically with shared x and y (same scale in every panel).
--csv writes PREFIX_<n>.csv with the normalized curves of each panel (provenance of the figure).
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import COL_W, FULL_W, plt, save  # noqa: E402

# Origin default sequence (user rule, 2026-11-09): 1 black, 2 red, 3 blue, 4 magenta -> Ag, Cr, O, Nd.
# 'okabe' = previous Okabe-Ito scheme, kept only for --palette okabe.
PALETTES = {
    'origin': ({'Ag': '#000000', 'Cr': '#FF0000', 'O': '#0000FF', 'Nd': '#FF00FF'},
               ['#008000', '#00FFFF', '#808000', '#800080']),
    'okabe': ({'Ag': '#D55E00', 'Cr': '#0072B2', 'O': '#009E73', 'Nd': '#CC79A7'},
              ['#E69F00', '#56B4E9', '#222222', '#8C6D31']),
}
COLORS, FALLBACK = PALETTES['origin']
TDOS_FILL, TDOS_EDGE = '#E3E3E3', '#7A7A7A'
BOX = dict(fc='white', ec='none', pad=1.0)  # solid, no alpha: keeps the dashed E_F line off the label


def species(folder):
    for name in ('CONTCAR', 'POSCAR'):
        p = os.path.join(folder, name)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            lines = open(p).read().split('\n')
            return lines[5].split(), [int(x) for x in lines[6].split()]
    raise FileNotFoundError(f'no CONTCAR/POSCAR in {folder}')


def read_doscar(folder):
    with open(os.path.join(folder, 'DOSCAR')) as f:
        natoms = int(f.readline().split()[0])
        for _ in range(4):
            f.readline()
        hdr = f.readline().split()
        nedos, efermi = int(hdr[2]), float(hdr[3])
        tot = np.array([f.readline().split() for _ in range(nedos)], dtype=float)
        spin = tot.shape[1] == 5
        if not spin:  # ISPIN=1 (non-magnetic reference): half of each density in each channel
            tot = np.column_stack([tot[:, 0], tot[:, 1] / 2, tot[:, 1] / 2, tot[:, 2] / 2, tot[:, 2] / 2])
        atoms = []
        for _ in range(natoms):
            f.readline()
            blk = np.array([f.readline().split() for _ in range(nedos)], dtype=float)
            if spin:
                atoms.append((blk[:, 1::2].sum(axis=1), blk[:, 2::2].sum(axis=1)))
            else:
                h = blk[:, 1:].sum(axis=1) / 2
                atoms.append((h, h))
    return natoms, efermi, tot, atoms


def broaden(e, y, sigma):
    if sigma <= 0:
        return y
    de = e[1] - e[0]
    x = np.arange(-int(5 * sigma / de), int(5 * sigma / de) + 1) * de
    g = np.exp(-0.5 * (x / sigma) ** 2)
    return np.convolve(y, g / g.sum(), mode='same')


def load_panel(folder, flip, sigma=0.0):
    els, counts = species(folder)
    natoms, ef, tot, atoms = read_doscar(folder)
    assert natoms == sum(counts), f'{folder}: DOSCAR has {natoms} atoms, POSCAR {sum(counts)}'
    e = tot[:, 0] - ef
    outcar = os.path.join(folder, 'OUTCAR')
    if os.path.isfile(outcar):
        nel = [float(l.split()[2]) for l in open(outcar) if 'NELECT' in l][:1]
        i_ef = np.searchsorted(tot[:, 0], ef) - 1
        integ = tot[i_ef, 3] + tot[i_ef, 4]
        if nel and abs(nel[0] / integ - 1) > 0.02:
            r = nel[0] / integ
            print(f'WARNING {folder}: DOSCAR TDOS integrates to {integ:.3f} at E_F, NELECT={nel[0]:.0f};'
                  f' rescaling TDOS by {r:.1f}', file=sys.stderr)
            tot[:, 1:3] *= r
    up, dn = tot[:, 1] / natoms, tot[:, 2] / natoms
    pd, i = {}, 0
    for el, n in zip(els, counts):
        u = sum(atoms[k][0] for k in range(i, i + n)) / n
        d = sum(atoms[k][1] for k in range(i, i + n)) / n
        pd[el] = (u, d)
        i += n
    i_ef = np.searchsorted(tot[:, 0], ef) - 1
    if flip == 'auto':
        flip = tot[i_ef, 3] < tot[i_ef, 4]
    up, dn = broaden(e, up, sigma), broaden(e, dn, sigma)
    pd = {k: (broaden(e, v[0], sigma), broaden(e, v[1], sigma)) for k, v in pd.items()}
    if flip:
        up, dn = dn, up
        pd = {k: (v[1], v[0]) for k, v in pd.items()}
    return e, (up, dn), pd, bool(flip)


def legend_entries(axes):
    """Unique legend entries over all panels (a pristine panel has no Nd line), in first-seen order."""
    seen = {}
    for ax in axes:
        for h, lab in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(lab, h)
    return list(seen.values()), list(seen.keys())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--panel', action='append', required=True, help='DIR:LABEL[:flip|:auto]')
    ap.add_argument('--out', required=True)
    ap.add_argument('--xlim', nargs=2, type=float, default=[-4.0, 4.0])
    ap.add_argument('--ylim', nargs=2, type=float, default=None)
    ap.add_argument('--width', choices=['single', 'double'], default='single')
    ap.add_argument('--panel-height', type=float, default=1.75, help='inches per panel')
    ap.add_argument('--csv', action='store_true')
    ap.add_argument('--legend-loc', default='lower left', help="legend place in the top panel (an empty corner), or 'top' = one row above the figure")
    ap.add_argument('--legend-ncol', type=int, default=2)
    ap.add_argument('--label-pos', choices=['ul', 'll'], default='ul', help='structure label: upper/lower left')
    ap.add_argument('--sigma', type=float, default=0.1, help='Gaussian broadening (std, eV); 0 = raw DOSCAR')
    ap.add_argument('--palette', choices=sorted(PALETTES), default='origin', help='line colours (default: Origin sequence)')
    a = ap.parse_args(argv)
    global COLORS, FALLBACK
    COLORS, FALLBACK = PALETTES[a.palette]

    plt.rcParams.update({'font.size': 10, 'axes.labelsize': 10, 'xtick.labelsize': 10, 'ytick.labelsize': 10,
                         'legend.fontsize': 9, 'font.family': 'serif',
                         'font.serif': ['Times New Roman', 'Liberation Serif', 'Nimbus Roman', 'STIXGeneral'],
                         'mathtext.fontset': 'stix', 'axes.linewidth': 0.8,
                         'xtick.direction': 'out', 'ytick.direction': 'out',
                         'pdf.fonttype': 42, 'ps.fonttype': 42})
    n = len(a.panel)
    w = COL_W if a.width == 'single' else FULL_W
    fig, axs = plt.subplots(n, 1, figsize=(w, 0.45 + a.panel_height * n), sharex=True, sharey=True,
                            constrained_layout=True, squeeze=False)
    ymax = 0.0
    for k, (ax, spec) in enumerate(zip(axs[:, 0], a.panel)):
        parts = spec.split(':')
        folder, label = parts[0], parts[1]
        flip = {'flip': True, 'auto': 'auto'}.get(parts[2], False) if len(parts) > 2 else False
        e, (tu, td), pd, flip = load_panel(folder, flip, a.sigma)
        print(f'{folder}: flip={flip}')
        win = (e >= a.xlim[0]) & (e <= a.xlim[1])
        ax.fill_between(e, 0, tu, color=TDOS_FILL, lw=0, label='Total')
        ax.fill_between(e, 0, -td, color=TDOS_FILL, lw=0)
        ax.plot(e, tu, color=TDOS_EDGE, lw=0.4)
        ax.plot(e, -td, color=TDOS_EDGE, lw=0.4)
        for j, (el, (u, d)) in enumerate(pd.items()):
            c = COLORS.get(el, FALLBACK[j % len(FALLBACK)])
            ax.plot(e, u, color=c, lw=0.9, label=el)
            ax.plot(e, -d, color=c, lw=0.9)
            ymax = max(ymax, u[win].max(), d[win].max())
        ax.axhline(0, color='k', lw=0.5)
        ax.axvline(0, color='k', lw=0.6, ls='--')
        if a.label_pos == 'ul':
            ax.text(0.03, 0.95, label, transform=ax.transAxes, ha='left', va='top', bbox=BOX)
        else:
            ax.text(0.03, 0.05, label, transform=ax.transAxes, ha='left', va='bottom', bbox=BOX)
        if n > 1:
            ax.text(-0.27 if n <= 3 else -0.2, 1.0, f'{chr(97 + k)})', transform=ax.transAxes, ha='left', va='top',
                    fontweight='bold')
        if n <= 3:
            ax.set_ylabel('DOS (states/eV/atom)')
        if a.csv:
            cols = [e, tu, -td] + [x for el in pd for x in (pd[el][0], -pd[el][1])]
            hdr = 'E-E_F(eV),Total_up,Total_down,' + ','.join(f'{el}_up,{el}_down' for el in pd)
            np.savetxt(f'{a.out}_{chr(97 + k)}.csv', np.column_stack(cols)[win], delimiter=',', fmt='%.5f',
                       header=f'# {os.path.abspath(folder)} flip={flip} sigma={a.sigma} eV; Total per cell atom, PDOS per species atom\n'
                              + hdr, comments='')
    lim = a.ylim or (-1.1 * ymax, 1.1 * ymax)
    axs[0, 0].set_ylim(*lim)
    axs[0, 0].set_xlim(*a.xlim)
    if n > 3:
        fig.supylabel('DOS (states/eV/atom)', fontsize=10)
    axs[-1, 0].set_xlabel(r'$E - E_\mathrm{F}$ (eV)')
    if a.legend_loc == 'top':
        h, lab = legend_entries(axs[:, 0])
        fig.legend(h, lab, loc='outside upper center', ncol=len(lab), frameon=False, handlelength=1.2,
                   columnspacing=0.8)
    else:
        h, lab = legend_entries(axs[:, 0])
        axs[0, 0].legend(h, lab, loc=a.legend_loc, ncol=a.legend_ncol, frameon=False, handlelength=1.4,
                         columnspacing=1.0)
    save(fig, a.out)


if __name__ == '__main__':
    main()
