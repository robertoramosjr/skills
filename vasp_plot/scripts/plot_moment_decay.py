#!/usr/bin/env python3
"""Fig. b: |induced magnetic moment| of Ag, Cr and O vs distance to Nd, points joined by lines (one curve per species).
Two stacked panels sharing x and y: (top) Nd_Ag without vacancies, (bottom) a vacancy-compensated structure.
The decay_*_raw_data.csv files hold |m| (no sign) per atom, sorted by distance.
Usage: plot_moment_decay.py --top <folder> --bottom <folder> [--top-label ... --bottom-label ...] --out <prefix>"""
import argparse, csv
from common import *
ap = argparse.ArgumentParser()
ap.add_argument('--top', required=True); ap.add_argument('--bottom', required=True)
ap.add_argument('--top-label', default='no vacancy'); ap.add_argument('--bottom-label', default='$\\mathrm{Nd}+2V_{\\mathrm{Ag}}$')
ap.add_argument('--out', required=True); ap.add_argument('--xmax', type=float, default=9.0)
a = ap.parse_args()
def load(folder, el):
    r = list(csv.DictReader(open(f'{folder}/decay_{el}_vs_Nd_raw_data.csv')))
    return [float(x['Distancia_A']) for x in r], [float(x['Momento_uB']) for x in r]
style(); fig, axs = plt.subplots(2, 1, figsize=(COL_W, 4.4), sharex=True, sharey=True, constrained_layout=True)
cols = {'Ag': 'C3', 'Cr': 'C0', 'O': 'C2'}; mk = {'Ag': 's', 'Cr': 'o', 'O': '^'}
for ax, folder, lab, tag in ((axs[0], a.top, a.top_label, '(a)'), (axs[1], a.bottom, a.bottom_label, '(b)')):
    for el in ('Ag', 'Cr', 'O'):
        x, y = load(folder, el); ax.plot(x, y, marker=mk[el], color=cols[el], ms=3, lw=0.8, label=el)
    ax.text(0.97, 0.93, f'{tag} {lab}', transform=ax.transAxes, ha='right', va='top')
    ax.set_ylabel(r'$|m|$ ($\mu_B$)'); ax.set_xlim(2, a.xmax)
axs[1].set_xlabel(r'distance to Nd ($\mathrm{\AA}$)'); axs[0].legend(loc='center right', frameon=False)
save(fig, a.out)
