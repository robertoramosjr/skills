#!/usr/bin/env python3
"""Atribuição de modos vibracionais para rotular picos de IR/FTIR calculado (Turbomole).

Por que: figura de IR sem indicar a que modo cada pico corresponde é fraca. O rótulo deve vir
dos MODOS NORMAIS CALCULADOS (não de memória nem de tabela de literatura) e ser rastreável.

Método (decomposição da energia cinética, KE, de cada modo normal):
  1. Lê `coord` (bohr), `vib_normal_modes` (deslocamentos cartesianos, norma 1, ortogonais na métrica de massa;
     coluna k = modo k, os 6 primeiros são translação/rotação) e `ir_dataset.dat` (modo, cm-1, km/mol).
  2. Constrói a conectividade por distância e, para cada átomo com >= 2 vizinhos, o plano local
     (normal n = u1 x u2, u = vetores até os dois vizinhos mais próximos).
  3. KE_i = m_i |d_i|^2 / sum(m |d|^2), decomposta por átomo em:
       H:  ao longo da ligação C-H        -> nu(C-H)
           no plano, perpendicular        -> delta(C-H)
           fora do plano (n)              -> gamma(C-H)
       N=N (dois N ligados entre si):  ao longo do eixo N-N -> nu(N=N);  restante no plano -> nu(C-N)/delta(CNN);
           fora do plano               -> torcao (CNNC)
       C (esqueleto): no plano -> anel (no plano);  fora do plano -> anel (fora do plano)
  4. Rótulo = categoria dominante (+ a segunda se KE >= SECOND). Símbolos: nu estiramento, delta flexão no plano,
     gamma flexão fora do plano. O resultado é um RÓTULO DE CARÁTER DOMINANTE, não uma PED completa:
     declarar isso na legenda/nota ("atribuição por decomposição da energia cinética dos modos normais calculados").

Uso:  python3 ir_mode_assign.py <pasta_turbomole> [--min-rel 0.12] [--table]
API:  assign_modes(folder) -> {modo: (rotulo, {categoria: fração})};  peak_labels(folder, top_n=5, merge=50) -> [(cm-1, int, texto)]
Regra de plot: rotular só os 5 picos mais intensos de cada espectro (rotular todos polui a figura).
"""
import sys, os, re, itertools
import numpy as np

MASS = {"h": 1.008, "c": 12.011, "n": 14.007, "o": 15.999, "s": 32.06}
BOHR = 0.529177210903
COV = {"h": 0.31, "c": 0.76, "n": 0.71, "o": 0.66, "s": 1.05}
CATS = ["nu(C–H)", "delta(C–H)", "gamma(C–H)", "nu(N=N)", "nu(C–N)", "torção CNNC", "anel no plano", "anel fora do plano"]
PRETTY = {"nu(C–H)": "ν(C–H)", "delta(C–H)": "δ(C–H)", "gamma(C–H)": "γ(C–H)", "nu(N=N)": "ν(N=N)", "nu(C–N)": "ν(C–N)",
          "torção CNNC": "CNNC torsion", "anel no plano": "ring ip", "anel fora do plano": "ring oop"}   # rótulos em inglês (figuras de artigo); ip/oop = in-plane/out-of-plane
SECOND = 0.22   # fração mínima da 2ª categoria para entrar no rótulo


def read_coord(path):
    el, xyz = [], []
    txt = open(path).read().split("$coord")[1].split("$")[0].strip().split("\n")
    for l in txt:
        p = l.split()
        xyz.append([float(v) for v in p[:3]]); el.append(p[3].lower())
    return el, np.array(xyz) * BOHR


def read_modes(path, n_atoms):
    rows = {}
    for l in open(path):
        p = l.split()
        if len(p) >= 3 and p[0].isdigit() and p[1].isdigit():
            rows.setdefault(int(p[0]), {})[int(p[1])] = [float(x.replace("D", "E")) for x in p[2:]]
    nr = 3 * n_atoms
    L = np.array([sum([rows[r][b] for b in sorted(rows[r])], []) for r in range(1, nr + 1)])
    return L  # (3N, nmodes)


def neighbors(el, xyz):
    n = len(el); nb = [[] for _ in range(n)]
    for i, j in itertools.combinations(range(n), 2):
        d = np.linalg.norm(xyz[i] - xyz[j])
        if d < 1.25 * (COV[el[i]] + COV[el[j]]) and not (el[i] == "h" and el[j] == "h"):
            nb[i].append(j); nb[j].append(i)
    return nb


def local_normal(i, xyz, nb):
    v = sorted(nb[i], key=lambda j: np.linalg.norm(xyz[j] - xyz[i]))
    if len(v) < 2: return None
    u1, u2 = xyz[v[0]] - xyz[i], xyz[v[1]] - xyz[i]
    n = np.cross(u1, u2); nn = np.linalg.norm(n)
    return n / nn if nn > 1e-6 else None


def assign_modes(folder):
    el, xyz = read_coord(os.path.join(folder, "coord"))
    N = len(el); L = read_modes(os.path.join(folder, "vib_normal_modes"), N)
    nb = neighbors(el, xyz); m = np.array([MASS[e] for e in el])
    nrm = [local_normal(i, xyz, nb) for i in range(N)]
    # fallback de normal para N (vizinhos C e N dão plano local) e H (usa o plano do C ligado)
    for i in range(N):
        if el[i] == "h" and nb[i]: nrm[i] = nrm[nb[i][0]]
    nn_pair = [(i, j) for i in range(N) for j in nb[i] if j > i and el[i] == "n" and el[j] == "n"]
    out = {}
    for k in range(L.shape[1]):
        d = L[:, k].reshape(N, 3); ke = m[:, None] * d ** 2; tot = (m * (d ** 2).sum(1)).sum()
        f = dict.fromkeys(CATS, 0.0)
        for i in range(N):
            di = d[i]; w = m[i]
            n = nrm[i]; oop = (di @ n) ** 2 if n is not None else 0.0; tot_i = (di ** 2).sum()
            if el[i] == "h" and nb[i]:
                u = xyz[i] - xyz[nb[i][0]]; u /= np.linalg.norm(u)
                par = (di @ u) ** 2
                f["nu(C–H)"] += w * par; f["gamma(C–H)"] += w * oop; f["delta(C–H)"] += w * max(tot_i - par - oop, 0)
            elif el[i] == "n" and any(i in p for p in nn_pair):
                p = [q for q in nn_pair if i in q][0]; ax = xyz[p[1]] - xyz[p[0]]; ax /= np.linalg.norm(ax)
                par = (di @ ax) ** 2
                f["nu(N=N)"] += w * par; f["torção CNNC"] += w * oop; f["nu(C–N)"] += w * max(tot_i - par - oop, 0)
            else:
                f["anel fora do plano"] += w * oop; f["anel no plano"] += w * max(tot_i - oop, 0)
        s = sum(f.values()); f = {c: v / s for c, v in f.items()}
        top = sorted(f.items(), key=lambda t: -t[1])
        lab = PRETTY[top[0][0]]
        if top[1][1] >= SECOND: lab += " + " + PRETTY[top[1][0]]
        out[k + 1] = (lab, f)
    return out


def peak_labels(folder, top_n=5, merge=50.0):
    """Rótulos para o plot: [(freq_cm1, intensidade, texto)] SÓ dos `top_n` picos mais intensos (padrão 5, regra do
    Roberto: rotular tudo polui). Escolha gulosa por intensidade; um pico a menos de `merge` cm-1 de outro já
    escolhido é pulado (evita rótulos sobrepostos). Devolve em ordem de frequência. texto = '718 · γ(C–H)'."""
    A = assign_modes(folder)
    d = np.loadtxt(os.path.join(folder, "ir_dataset.dat"), skiprows=1)
    chosen = []
    for mo, w, I in sorted(d.tolist(), key=lambda t: -t[2]):
        if len(chosen) >= top_n: break
        if int(mo) in A and all(abs(w - c[0]) >= merge for c in chosen): chosen.append((w, I, int(mo)))
    return [(w, I, f"{w:.0f} · {A[mo][0]}") for w, I, mo in sorted(chosen)]


if __name__ == "__main__":
    folder = sys.argv[1]; min_rel = float(sys.argv[sys.argv.index("--min-rel") + 1]) if "--min-rel" in sys.argv else 0.12
    d = np.loadtxt(os.path.join(folder, "ir_dataset.dat"), skiprows=1)
    A = assign_modes(folder)
    print(f"{'modo':>4} {'cm-1':>8} {'km/mol':>8}  rótulo   [frações KE]")
    mx = d[:, 2].max()
    for mo, w, I in d:
        if I >= min_rel * mx or "--table" in sys.argv:
            lab, f = A[int(mo)]
            fr = "  ".join(f"{c.split('(')[0][:5]}{c[c.find('('):] if '(' in c else ''}={v:.2f}" for c, v in sorted(f.items(), key=lambda t: -t[1])[:3])
            print(f"{int(mo):4d} {w:8.1f} {I:8.1f}  {lab:36s} {fr}")
