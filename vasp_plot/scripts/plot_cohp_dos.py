#!/usr/bin/env python3
"""DOS + -pCOHP lado a lado (eixo de energia comum, E_F = 0), no estilo da Fig. 7 de
CaMnTeO6 (arXiv 2403.08069): spin-up azul, spin-down vermelho, total preto, caixa com -ICOHP.
Entrada: pasta do LOBSTER (COHPCAR.lobster, DOSCAR.lobster, lobster_atoms.csv).
  plot_cohp_dos.py <pasta> [saida_sem_ext] [--emin -6] [--emax 4] [--center Nd]
Curvas = média sobre as ligações do grupo (mesma normalização do -ICOHP por ligação).
Painéis: DOS (total + centro), centro–O, Cr–O (todas), Cr–O dos Cr vizinhos do centro, Ag–O (<2,6 Å).
Layout COHPCAR (verificado vs ICOHPLIST): col 0 = E; entrada k (0 = média, n = No.n)
  up: cols 1+2k (COHP), 2+2k (ICOHP); dn: mesmas + 2*(N+1)... N = nº de entradas."""
import re, sys, csv, argparse, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker, matplotlib.transforms

ap = argparse.ArgumentParser()
ap.add_argument("dir"); ap.add_argument("out", nargs="?")
ap.add_argument("--emin", type=float, default=-3); ap.add_argument("--emax", type=float, default=3)
ap.add_argument("--center", default="Nd"); ap.add_argument("--near", type=float, default=4.0,
                help="Cr com d(centro) < near (Å) = 'vizinhos'")
ap.add_argument("--agO", type=float, default=2.6)
a = ap.parse_args()
out = a.out or os.path.join(a.dir, "cohp_dos")

# ---- COHPCAR
L = open(os.path.join(a.dir, "COHPCAR.lobster")).read().split("\n")
nent = int(L[1].split()[0])
lab = [(i, l) for i, l in enumerate(L) if l.startswith("No.")]
first = lab[-1][0] + 1
D = np.array([l.split() for l in L[first:] if l.strip()], float)
E = D[:, 0]
bonds = {}  # n -> (a1, a2, d)
# coluna da entrada = posição da linha de rótulo (as orbitais têm coluna própria; o nº "No." se repete)
for k, (i, l) in enumerate(lab, 1):
    m = re.match(r"No\.(\d+):([A-Za-z]+\d+)->([A-Za-z]+\d+)\(([\d.]+)\)$", l)
    if m:
        bonds[k] = (m.group(2), m.group(3), float(m.group(4)))
el = lambda s: re.match(r"[A-Za-z]+", s).group(0)
off = 1 + 2 * nent
def curve(n, spin):          # -pCOHP e ICOHP(E_F) da ligação n
    c = 1 + 2 * n + (off - 1) * spin
    return -D[:, c], -D[np.argmin(abs(E)), c + 1]

atoms = list(csv.DictReader(open(os.path.join(a.dir, "lobster_atoms.csv"))))
near_cr = {f"Cr{r['atom']}" for r in atoms if r["el"] == "Cr" and float(r["d_center"]) < a.near}

def group(sel):
    ns = [n for n, (x, y, d) in bonds.items() if sel(x, y, d)]
    res = {}
    for s, k in ((0, "up"), (1, "dn")):
        cs = [curve(n, s) for n in ns]
        res[k] = (np.mean([c[0] for c in cs], 0), np.mean([c[1] for c in cs]))
    res["tot"] = (res["up"][0] + res["dn"][0], res["up"][1] + res["dn"][1])
    return res, len(ns)

pair = lambda x, y, e1, e2: {el(x), el(y)} == {e1, e2}
groups = [
    (f"{a.center}–O", lambda x, y, d: pair(x, y, a.center, "O")),
    ("Cr–O (all)", lambda x, y, d: pair(x, y, "Cr", "O")),
    ("Ag–O (all)", lambda x, y, d: pair(x, y, "Ag", "O")),
]

# ---- DOS (DOSCAR.lobster: bloco total + 1 bloco por átomo)
DL = open(os.path.join(a.dir, "DOSCAR.lobster")).read().split("\n")
nat = int(DL[0].split()[0]); npt = int(DL[5].split()[2])
blk = lambda s: np.array([l.split() for l in DL[s:s + npt]], float)
tot = blk(6)
ncol = len(DL[6 + npt + 1].split())
atom_blocks = []
p = 6 + npt
while len(atom_blocks) < nat:
    atom_blocks.append(blk(p + 1)); p += npt + 1
cidx = [i for i, r in enumerate(atoms) if r["el"] == a.center]
cen = atom_blocks[int(atoms[cidx[0]]["atom"]) - 1]
cen_up, cen_dn = cen[:, 1::2].sum(1), cen[:, 2::2].sum(1)
Ed = tot[:, 0]

plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "dejavuserif", "xtick.direction": "in",
                     "ytick.direction": "in", "font.size": 8})
nP = 1 + len(groups)
fig, axs = plt.subplots(1, nP, figsize=(7.0, 3.3), sharey=True, gridspec_kw={"wspace": 0.0})
B, R, K = "tab:blue", "tab:red", "k"
ax = axs[0]
ax.plot(tot[:, 1], Ed, color=B, lw=0.7); ax.plot(-tot[:, 2], Ed, color=R, lw=0.7)
ax.fill_betweenx(Ed, cen_up * 5, color=B, alpha=0.35, lw=0); ax.fill_betweenx(Ed, -cen_dn * 5, color=R, alpha=0.35, lw=0)
ax.plot([], [], color="0.4", lw=0.7, label="total"); ax.fill_between([], [], color="0.4", alpha=0.35, label=f"{a.center} ×5")
ax.legend(frameon=False, loc="upper right", fontsize=6.5, handlelength=1.0, borderaxespad=0.2)
ax.set_xlabel("DOS (states/eV)"); ax.set_ylabel(r"$E-E_F$ (eV)")
for ax, (name, sel) in zip(axs[1:], groups):
    g, n = group(sel)
    ax.plot(g["up"][0], E, color=B, lw=0.7); ax.plot(g["dn"][0], E, color=R, lw=0.7); ax.plot(g["tot"][0], E, color=K, lw=0.8)
    ax.set_xlabel(r"$-$pCOHP (eV)")
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(3, prune="both"))
    w = (E >= a.emin) & (E <= a.emax)
    lo = min(g[k][0][w].min() for k in ("up", "dn", "tot")); hi = max(g[k][0][w].max() for k in ("up", "dn", "tot"))
    pad = 0.08 * (hi - lo)
    ax.set_xlim(lo - pad, hi + 0.8 * (hi - lo))   # folga à direita p/ o texto (no gap)
    w = (E >= a.emin) & (E <= a.emax)
    lo = min(g[k][0][w].min() for k in ("up", "dn", "tot")); hi = max(g[k][0][w].max() for k in ("up", "dn", "tot"))
    pad = 0.08 * (hi - lo)
    ax.set_xlim(lo - pad, hi + 0.8 * (hi - lo))   # folga à direita p/ o texto (no gap)
    ax.text(0.97, -0.55, f"{name}\n{n} bonds\n" r"$-$ICOHP " f"{g['tot'][1]:.2f}\n"
            r"$\uparrow$" f"{g['up'][1]:.2f} " r"$\downarrow$" f"{g['dn'][1]:.2f}",
            transform=matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData), ha="right", va="center", fontsize=6, linespacing=1.2)
for ax in axs:
    ax.axhline(0, color="0.4", lw=0.5, ls="--"); ax.axvline(0, color="0.6", lw=0.4)
    ax.set_ylim(a.emin, a.emax); ax.tick_params(labelsize=7)
    ax.set_yticks(range(int(np.ceil(a.emin)), int(a.emax) + 1, 2))
for ax in axs[1:]:
    ax.tick_params(left=False)
# xlim por painel: simétrico no DOS, COHP auto com margem
fig.subplots_adjust(left=0.08, right=0.99, bottom=0.14, top=0.98)
fig.savefig(out + ".png", dpi=300); fig.savefig(out + ".eps")
print("ok", out, "near_cr:", sorted(near_cr))
