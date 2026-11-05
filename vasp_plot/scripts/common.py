"""Shared style for vasp_plot: 10 pt text at printed width (revtex4-2 prb, 10 pt body)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
COL_W = 3.39   # in, revtex4-2 aps single column (~86 mm)
FULL_W = 7.0   # in, figure*
def style():
    plt.rcParams.update({'font.size': 10, 'axes.labelsize': 10, 'xtick.labelsize': 10, 'ytick.labelsize': 10,
        'legend.fontsize': 10, 'font.family': 'serif', 'mathtext.fontset': 'dejavuserif',
        'axes.linewidth': 0.8, 'xtick.direction': 'in', 'ytick.direction': 'in',
        'xtick.top': True, 'ytick.right': True, 'ps.useafm': True, 'pdf.fonttype': 42, 'ps.fonttype': 42})
def save(fig, prefix):
    fig.savefig(prefix + '.eps'); fig.savefig(prefix + '.png', dpi=300)
    print('wrote', prefix + '.eps', prefix + '.png')
