#!/usr/bin/env python3
"""Parse CRYSTAL23 outputs for the pipeline (validation by TEXT, never by exit code / queue state).

Subcommands:
  check  OUT...           termination, SCF/opt convergence, energy, gap, wall time  (exit 1 if any fails)
  kconv  PARENT|DIR...    k-convergence table as the VASP extract_stress_data.py (l, mesh, cell, E, folder)
                          + dE meV/atom and dV % vs the densest mesh, gap -> PARENT/dados_convergencia_final.csv
  opt    OUT              optimization summary: converged?, points, final cell and volume, energy
  dos    DIR              DOSS.DAT (+fort.25 for E_F) -> DOS_raw_data.csv (eV, states/eV/cell)
  bands  DIR              fort.25 BAND blocks -> bands.csv (k-distance, E-E_F in eV) + VBM/CBM/gap

Usage:
  cry_parse.py check runs/*/crystal.out
  cry_parse.py kconv runs/hse_stress_kconv
  cry_parse.py opt runs/hse_fullopt/crystal.out
  cry_parse.py dos runs/hse_sp ; cry_parse.py bands runs/hse_sp
"""
import argparse
import csv
import re
import sys
from pathlib import Path

HA_EV = 27.211386245988


def txt(p):
    return Path(p).read_text(errors="replace")


def last(pattern, t, cast=float, default=None):
    m = re.findall(pattern, t, re.M)
    return cast(m[-1]) if m else default


def summary(out):
    t = txt(out)
    s = {"file": str(out)}
    s["terminated"] = "EEEEEEEEEE TERMINATION" in t
    s["scf_ok"] = "SCF ENDED - CONVERGENCE" in t
    s["scf_fail"] = bool(re.search(r"SCF ENDED - TOO MANY CYCLES|SCF NOT CONVERGED", t))
    s["is_opt"] = "OPTIMIZATION STARTS" in t
    s["opt_ok"] = "OPT END - CONVERGED" in t
    s["energy_ha"] = last(r"OPT END - CONVERGED.*?E\(AU\):\s*(-?\d+\.\d+E[+-]\d+)", t) if s["opt_ok"] \
        else last(r"SCF ENDED - CONVERGENCE ON ENERGY\s+E\(AU\)\s+(-?\d\.\d+E[+-]\d+)", t)
    s["opt_points"] = last(r"OPTIMIZATION - POINT\s+(\d+)", t, int)
    g = re.findall(r"(DIRECT|INDIRECT) ENERGY BAND GAP:\s+([\d.]+)", t)
    s["gap_ev"], s["gap_type"] = (float(g[-1][1]), g[-1][0]) if g else (None, None)
    s["conducting"] = "POSSIBLY CONDUCTING STATE" in t[-200000:]
    s["nat"] = last(r"N\. OF ATOMS PER CELL\s+(\d+)", t, int)
    k = re.findall(r"SHRINK\. FACT\.\(MONKH\.\)\s+(\d+)\s+(\d+)\s+(\d+)\s+NUMBER OF K POINTS IN THE IBZ\s+(\d+)", t)
    s["kmesh"], s["nk_ibz"] = ("x".join(k[-1][:3]), int(k[-1][3])) if k else (None, None)
    s["wall_s"] = last(r"TTTTT+ END\s+TELAPSE\s+([\d.]+)", t)
    s["volume_A3"] = last(r"PRIMITIVE CELL - CENTRING CODE.*?VOLUME=\s*([\d.]+)", t)  # last printed cell
    s["errors"] = sorted(set(re.findall(r"ERROR \*+ ?([A-Z0-9_ ]{3,40})", t)))[:5]
    return s


def cmd_check(a):
    bad = 0
    for o in a.out:
        s = summary(o)
        ok = s["terminated"] and s["scf_ok"] and not s["scf_fail"] and (s["opt_ok"] or not s["is_opt"])
        bad += not ok
        e = f"{s['energy_ha']:.10f}" if s["energy_ha"] is not None else "-"
        gap = f"{s['gap_type']} {s['gap_ev']} eV" if s["gap_ev"] else ("CONDUCTING?" if s["conducting"] else "-")
        print(f"{'OK  ' if ok else 'FAIL'} {o}: term={s['terminated']} scf={s['scf_ok']} "
              f"opt={'-' if not s['is_opt'] else s['opt_ok']}({s['opt_points']} pts) E={e} Ha "
              f"k={s['kmesh']}/{s['nk_ibz']} gap={gap} wall={s['wall_s']} s {' '.join(s['errors'])}")
    sys.exit(1 if bad else 0)


def cell_params(t):
    """Last printed primitive cell (a b c alpha beta gamma, V) from a crystal.out text."""
    m = list(re.finditer(r"PRIMITIVE CELL - CENTRING CODE.*?VOLUME=\s*([\d.]+).*?GAMMA\s*\n\s*([-\d.\s]+?)\n", t, re.S))
    if not m:
        return None, None
    return [float(x) for x in m[-1].group(2).split()[:6]], float(m[-1].group(1))


def cmd_kconv(a):
    """VASP-style table (extract_stress_data.py): Kdensity, Kmesh, lattice, Energy, folder (+dE, dV, gap)."""
    dirs = []
    for d in map(Path, a.dirs):
        subs = sorted(x for x in d.iterdir() if (x / "INPUT").exists()) if d.is_dir() and not (d / "INPUT").exists() else []
        dirs += subs or [d]
    parent = Path(a.dirs[0]) if len(a.dirs) == 1 and Path(a.dirs[0]).is_dir() and not (Path(a.dirs[0]) / "INPUT").exists() else None
    rows = []
    for d in dirs:
        o = d / "crystal.out" if d.is_dir() else d
        if not o.exists():
            print(f"skip {d}: no crystal.out", file=sys.stderr)
            continue
        s = summary(o)
        done = s["terminated"] and s["scf_ok"] and (s["opt_ok"] or not s["is_opt"])
        if not done:
            print(f"skip {d}: not finished/converged (term={s['terminated']} scf={s['scf_ok']} opt={s['opt_ok']})", file=sys.stderr)
            continue
        cell, vol = cell_params(txt(o))
        kk = [int(x) for x in s["kmesh"].split("x")]
        rows.append({"Kdensity": d.name, "Kmesh": s["kmesh"], "nk_ibz": s["nk_ibz"], "nat": s["nat"],
                     "a": cell[0], "b": cell[1], "c": cell[2], "alpha": cell[3], "beta": cell[4], "gamma": cell[5],
                     "V_A3": vol, "Energy_Ha": s["energy_ha"], "gap_eV": s["gap_ev"], "opt": s["is_opt"],
                     "wall_s": s["wall_s"], "Pasta": str(d), "_n": kk[0] * kk[1] * kk[2]})
    if parent and (parent / "kmesh_map.txt").exists():  # repeated meshes: same result, listed for completeness
        byname = {r["Kdensity"]: r for r in rows}
        for l in (parent / "kmesh_map.txt").read_text().splitlines():
            t = l.split()
            if len(t) == 4 and t[2] == "same_as" and t[3] in byname:
                rows.append(dict(byname[t[3]], Kdensity=t[0], Pasta=f"(= {t[3]})"))
    if not rows:
        sys.exit("no finished runs")
    rows.sort(key=lambda r: (r["_n"], r["Kdensity"]))
    ref = max(rows, key=lambda r: r["_n"])
    for r in rows:
        r["dE_meV_atom_vs_densest"] = (r["Energy_Ha"] - ref["Energy_Ha"]) * HA_EV * 1000 / r["nat"]
        r["dV_pct_vs_densest"] = 100 * (r["V_A3"] - ref["V_A3"]) / ref["V_A3"]
    print(f"{'l':>3} {'kmesh':>9} {'nkIBZ':>5} {'a':>9} {'b':>9} {'c':>9} {'V A3':>10} {'E (Ha)':>19} "
          f"{'dE meV/at':>9} {'dV %':>7} {'gap eV':>7}  folder")
    for r in rows:
        print(f"{r['Kdensity']:>3} {r['Kmesh']:>9} {r['nk_ibz']:>5} {r['a']:>9.5f} {r['b']:>9.5f} {r['c']:>9.5f} "
              f"{r['V_A3']:>10.4f} {r['Energy_Ha']:>19.10f} {r['dE_meV_atom_vs_densest']:>9.3f} "
              f"{r['dV_pct_vs_densest']:>7.3f} {r['gap_eV'] if r['gap_eV'] is not None else '-':>7}  {r['Pasta']}")
    if not all(r["opt"] for r in rows):
        print("note: single-point rows (no optimization): dV is meaningless there", file=sys.stderr)
    out = a.csv or (str(parent / "dados_convergencia_final.csv") if parent else None)
    if out:
        keys = ["Kdensity", "Kmesh", "nk_ibz", "a", "b", "c", "alpha", "beta", "gamma", "V_A3", "Energy_Ha",
                "dE_meV_atom_vs_densest", "dV_pct_vs_densest", "gap_eV", "wall_s", "Pasta"]
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("written", out)


def cmd_opt(a):
    t = txt(a.out)
    s = summary(a.out)
    i = t.rfind("FINAL OPTIMIZED GEOMETRY")
    seg = t[i:] if i >= 0 else t[t.rfind("PRIMITIVE CELL - CENTRING CODE"):]
    m = re.search(r"PRIMITIVE CELL - CENTRING CODE.*?VOLUME=\s*([\d.]+).*?GAMMA\s*\n\s*([-\d.\s]+)\n", seg, re.S)
    print(f"converged={s['opt_ok']} points={s['opt_points']} E={s['energy_ha']} Ha  terminated={s['terminated']}")
    if i < 0:
        print("WARNING: no 'FINAL OPTIMIZED GEOMETRY' block: cell below is the LAST printed, not final")
    if m:
        print(f"V = {m.group(1)} A^3   a b c alpha beta gamma = {' '.join(m.group(2).split()[:6])}")
    for f in ("fort.34", "OPTINFO.DAT", "HESSOPT.DAT"):
        print(f"{f}: {'present' if (Path(a.out).parent / f).exists() else 'missing'}")


def fermi_from_f25(d, typ):
    f = Path(d) / "fort.25"
    if not f.exists():
        return None
    for l in f.read_text().splitlines():
        if l.startswith("-%-") and typ in l:
            return float(l[-12:])  # last E12.5 field: E_F (BAND) / COSXY = E_F (DOSS)
    return None


def cmd_dos(a):
    d = Path(a.dir)
    lines = (d / "DOSS.DAT").read_text().splitlines()
    head = re.search(r"NEPTS\s+(\d+)\s+NPROJ\s+(\d+)\s+NSPIN\s+(\d+)", lines[0])
    npro1, nspin = int(head.group(2)), int(head.group(3))
    data = [list(map(float, l.split())) for l in lines if l.strip() and not l.lstrip().startswith(("#", "@"))]
    ef = fermi_from_f25(d, "DOSS")
    relative = any("E-EFERMI" in l for l in lines[:5])  # CRYSTAL23 writes E - E_F already (verified MgO test)
    shift = 0.0 if relative else (ef or 0.0)
    out = d / "DOS_raw_data.csv"
    ncol = len(data[0]) - 1
    names = [f"pdos{j + 1}_states_per_eV" for j in range(ncol - 1)] + ["total_states_per_eV"]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["E_minus_EF_eV" if (relative or ef is not None) else "E_eV"] + names)
        for r in data:
            w.writerow([f"{(r[0] - shift) * HA_EV:.6f}"] + [f"{x / HA_EV:.6e}" for x in r[1:]])
    de = (data[-1][0] - data[0][0]) * HA_EV / max(1, len(data) - 1) * 1000
    if de > 20:
        print(f"WARNING: DOS step {de:.0f} meV (window includes deep/core bands?): narrow INZB/IFNB in PROPS")
    print(f"written {out}: {len(data)} rows, step {de:.1f} meV, NPROJ(+total)={npro1}, NSPIN={nspin}, E_F={ef} Ha. "
          "Columns: PDOS projections in PROPS order (cry_props prints it), total DOS last (sum checked on MgO).")


def cmd_bands(a):
    d = Path(a.dir)
    L = (d / "fort.25").read_text().splitlines()
    segs, i = [], 0
    while i < len(L):
        l = L[i]
        if l.startswith("-%-") and "BAND" in l:
            nb, nk = int(l[8:13]), int(l[13:18])
            dk, ef = float(l[30:42]), float(l[42:54])
            vals, j = [], i + 3
            while len(vals) < nb * nk:
                row = L[j]
                vals += [float(row[c:c + 12]) for c in range(0, len(row.rstrip()), 12)]
                j += 1
            segs.append((nb, nk, dk, ef, vals))
            i = j
        else:
            i += 1
    if not segs:
        sys.exit("no BAND blocks in fort.25")
    nb, ef = segs[0][0], segs[0][3]
    kd, eig, x, segof = [], [], 0.0, []
    for si, (nb_, nk, dk, _, vals) in enumerate(segs):
        for j in range(nk):
            kd.append(x + j * dk)
            eig.append(vals[j * nb_:(j + 1) * nb_])
            segof.append((si, j, nk))
        x += (nk - 1) * dk
    kpf = d / "KPATH_CRYSTAL"
    seglab = [l.split()[6:8] for l in kpf.read_text().splitlines() if l.strip() and l[0] not in "#ID"] \
        if kpf.exists() else []

    def where(k):
        si, j, nk = segof[k]
        if len(seglab) != len(segs):
            return f"segment {si + 1}, point {j + 1}/{nk}"
        a, b = seglab[si]
        return a if j == 0 else b if j == nk - 1 else f"{a}-{b} ({j}/{nk - 1})"
    # conduction = first band lying entirely above E_F. NOT "occupied if max <= E_F": E_F comes from the SCF
    # net, and along the path the valence band can rise above it (Ag2SeO3 B3LYP k333: +0.07 eV).
    cbl = [b for b in range(nb) if min(e[b] for e in eig) > ef + 1e-4]
    cb = cbl[0] if cbl else None
    vb = cb - 1 if cb else None
    with open(d / "bands.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["k_dist_bohr-1"] + [f"band{b + 1}" for b in range(nb)])
        for k, e in zip(kd, eig):
            w.writerow([f"{k:.6f}"] + [f"{(v - ef) * HA_EV:.5f}" for v in e])
    if kpf.exists():  # tick positions/labels for plotting (segment starts + final end)
        labs = [l.split()[6:8] for l in kpf.read_text().splitlines() if l.strip() and l[0] not in "#ID"]
        if len(labs) == len(segs):
            ticks, x = [], 0.0
            for (nb_, nk, dk, _, _), (la, lb) in zip(segs, labs):
                if ticks and ticks[-1][1] != la:
                    ticks[-1] = (ticks[-1][0], f"{ticks[-1][1]}|{la}")
                elif not ticks:
                    ticks.append((x, la))
                x += (nk - 1) * dk
                ticks.append((x, lb))
            with open(d / "bands_ticks.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["k_dist_bohr-1", "label"])
                w.writerows([(f"{t:.6f}", l) for t, l in ticks])
    msg = f"written {d / 'bands.csv'}: {len(segs)} segments, {len(kd)} k, {nb} bands, E_F={ef:.6f} Ha"
    if vb is not None and vb >= 0:
        vbm = max(range(len(eig)), key=lambda k: eig[k][vb])
        cbm = min(range(len(eig)), key=lambda k: eig[k][cb])
        gap = (eig[cbm][cb] - eig[vbm][vb]) * HA_EV
        direct = abs(kd[vbm] - kd[cbm]) < 1e-9
        msg += (f"\n  VBM at {where(vbm)} (k={kd[vbm]:.4f}), CBM at {where(cbm)} (k={kd[cbm]:.4f}), "
                f"gap along path = {gap:.4f} eV, {'direct' if direct else 'indirect'} "
                "(path only; compare with the SCF-net gap)")
    print(msg)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("check"); c.add_argument("out", nargs="+"); c.set_defaults(f=cmd_check)
    c = sp.add_parser("kconv"); c.add_argument("dirs", nargs="+"); c.add_argument("--csv"); c.set_defaults(f=cmd_kconv)
    c = sp.add_parser("opt"); c.add_argument("out"); c.set_defaults(f=cmd_opt)
    c = sp.add_parser("dos"); c.add_argument("dir"); c.set_defaults(f=cmd_dos)
    c = sp.add_parser("bands"); c.add_argument("dir"); c.set_defaults(f=cmd_bands)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
