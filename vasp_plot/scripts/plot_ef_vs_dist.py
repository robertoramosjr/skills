#!/usr/bin/env python3
"""Fig. a: formation energy (left y) and Delta E (right y) vs Nd--V_Ag distance, points joined by a line.
x = mean of the two Nd--vacancy distances d1,d2 (horizontal bar = d1..d2).
Usage: plot_ef_vs_dist.py --etot-dir <paw_pbe_1.125xENMAX_Etot> --out <prefix> [--csv out.csv]"""
import argparse, glob, os, subprocess, csv, numpy as np
from common import *
def rd(p):
    L = open(p).read().split('\n'); s = float(L[1]); A = np.array([[float(x) for x in L[i].split()] for i in (2, 3, 4)]) * s
    el = L[5].split(); n = list(map(int, L[6].split())); o = 7
    if L[o].strip()[0] in 'Ss': o += 1
    c = np.array([[float(x) for x in L[o + 1 + i].split()[:3]] for i in range(sum(n))]); idx = np.cumsum([0] + n)
    return A, {e: c[idx[i]:idx[i + 1]] for i, e in enumerate(el)}
def dist(a, b, A):
    d = a - b; d -= np.round(d); return np.linalg.norm(d @ A, axis=-1)
def e0(p): return float(subprocess.check_output(f"grep 'energy  without entropy' {p} | tail -1 | awk '{{print $7}}'", shell=True))
ap = argparse.ArgumentParser(); ap.add_argument('--etot-dir', required=True); ap.add_argument('--out', required=True); ap.add_argument('--csv')
a = ap.parse_args(); R = a.etot_dir; D = f'{R}/DEFECT_MODELS'
# chemical potentials (elemental, Nd spin-polarized) and pristine 224-atom energy
mu = {}
for r in csv.DictReader(open(f'{D}/Ef_calc/pure_bulk.csv')): mu[r['Folder']] = float(r['Energy_eV']) / float(r['Atoms'])
E_pris = e0(f'{R}/OUTCAR') * 8       # 28-atom cell x 8
term = mu['Nd'] - 3 * mu['Ag']
A, ref = rd(f'{D}/Ag_by_Nd_1_1/CONTCAR')
rows = []
for d in sorted(glob.glob(f'{D}/Ag_by_Nd_1_1/vacancies_compensation/Ag_*_OK')):
    A2, c = rd(d + '/CONTCAR'); vac = [i for i, p in enumerate(ref['Ag']) if dist(p, c['Ag'], A).min() > 1.5]
    dv = sorted(float(dist(ref['Ag'][i], c['Nd'][0], A)) for i in vac)
    rows.append((os.path.basename(d)[:-3], dv[0], dv[1], e0(d + '/OUTCAR') - E_pris - term))
rows.sort(key=lambda r: (r[1] + r[2]) / 2); emin = min(r[3] for r in rows)
if a.csv:
    with open(a.csv, 'w') as f:
        f.write('structure,d1_A,d2_A,dmean_A,Ef_eV,dE_eV\n')
        for n, d1, d2, ef in rows: f.write(f'{n},{d1:.3f},{d2:.3f},{(d1+d2)/2:.3f},{ef:.4f},{ef-emin:.4f}\n')
style(); fig, ax = plt.subplots(figsize=(COL_W, 2.7), constrained_layout=True)
x = np.array([(r[1] + r[2]) / 2 for r in rows]); y = np.array([r[3] for r in rows])
xe = np.array([[x[i] - rows[i][1] for i in range(len(rows))], [rows[i][2] - x[i] for i in range(len(rows))]])
ax.errorbar(x, y, xerr=xe, fmt='o-', color='C0', ms=4, lw=1, elinewidth=0.6, capsize=2)
for xi, yi, r in zip(x, y, rows): ax.annotate(r[0].replace('Ag_', ''), (xi, yi), textcoords='offset points', xytext=(0, 5), ha='center', fontsize=6)
ax.set_xlabel(r'$d(\mathrm{Nd}\!-\!V_{\mathrm{Ag}})$ ($\mathrm{\AA}$)'); ax.set_ylabel(r'$E_f$ (eV)')
lo, hi = ax.get_ylim(); ax2 = ax.twinx(); ax2.set_ylim(lo - emin, hi - emin); ax2.set_ylabel(r'$\Delta E$ (eV)'); ax2.tick_params(direction='in')
save(fig, a.out)
