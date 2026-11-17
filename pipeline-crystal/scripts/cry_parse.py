#!/usr/bin/env python3
"""Parse CRYSTAL23 outputs for the pipeline (validation by TEXT, never by exit code / queue state).

Subcommands:
  check  OUT...           termination, SCF/opt convergence, energy, gap, wall time  (exit 1 if any fails)
  kconv  DIR...           k-mesh convergence table (dE meV/atom vs the densest mesh, gap) -> CSV
  opt    OUT              optimization summary: converged?, points, final cell and volume, energy
  dos    DIR              DOSS.DAT (+fort.25 for E_F) -> DOS_raw_data.csv (eV, states/eV/cell)
  bands  DIR              fort.25 BAND blocks -> bands.csv (k-distance, E-E_F in eV) + VBM/CBM/gap

Usage:
  cry_parse.py check runs/*/crystal.out
  cry_parse.py kconv runs/hse_kconv_k* --csv kconv.csv
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


def cmd_kconv(a):
    rows = []
    for d in a.dirs:
        o = Path(d) / "crystal.out" if Path(d).is_dir() else Path(d)
        if not o.exists():
            print(f"skip {d}: no crystal.out", file=sys.stderr)
            continue
        s = summary(o)
        if not (s["terminated"] and s["scf_ok"]):
            print(f"skip {d}: not finished/converged", file=sys.stderr)
            continue
        kk = [int(x) for x in s["kmesh"].split("x")]
        rows.append({"dir": str(d), "kmesh": s["kmesh"], "nk_ibz": s["nk_ibz"], "nat": s["nat"],
                     "E_Ha": s["energy_ha"], "gap_eV": s["gap_ev"], "wall_s": s["wall_s"], "V_A3": s["volume_A3"],
                     "opt": s["is_opt"], "_n": kk[0] * kk[1] * kk[2]})
        if s["is_opt"] and not s["opt_ok"]:
            print(f"WARNING {d}: optimization NOT converged", file=sys.stderr)
    if not rows:
        sys.exit("no finished runs")
    rows.sort(key=lambda r: r["_n"])
    ref = rows[-1]
    for r in rows:
        r["dE_meV_atom_vs_densest"] = (r["E_Ha"] - ref["E_Ha"]) * HA_EV * 1000 / r["nat"]
        r["dV_pct_vs_densest"] = (100 * (r["V_A3"] - ref["V_A3"]) / ref["V_A3"]) if (r["opt"] and ref["V_A3"]) else None
    print(f"{'kmesh':>9} {'nkIBZ':>5} {'E (Ha)':>20} {'dE meV/at':>10} {'dV %':>7} {'gap eV':>7} {'wall s':>8}  dir")
    for r in rows:
        dv = f"{r['dV_pct_vs_densest']:.3f}" if r["dV_pct_vs_densest"] is not None else "-"
        print(f"{r['kmesh']:>9} {r['nk_ibz']:>5} {r['E_Ha']:>20.10f} {r['dE_meV_atom_vs_densest']:>10.3f} {dv:>7} "
              f"{r['gap_eV'] if r['gap_eV'] is not None else '-':>7} {r['wall_s'] or '-':>8}  {r['dir']}")
    if a.csv:
        keys = ["kmesh", "nk_ibz", "nat", "E_Ha", "dE_meV_atom_vs_densest", "V_A3", "dV_pct_vs_densest", "gap_eV", "wall_s", "dir"]
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("written", a.csv)


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
    kd, eig, x = [], [], 0.0
    for nb_, nk, dk, _, vals in segs:
        for j in range(nk):
            kd.append(x + j * dk)
            eig.append(vals[j * nb_:(j + 1) * nb_])
        x += (nk - 1) * dk
    occ = [b for b in range(nb) if max(e[b] for e in eig) <= ef + 1e-5]
    vb, cb = (max(occ), max(occ) + 1) if occ else (None, None)
    with open(d / "bands.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["k_dist_bohr-1"] + [f"band{b + 1}" for b in range(nb)])
        for k, e in zip(kd, eig):
            w.writerow([f"{k:.6f}"] + [f"{(v - ef) * HA_EV:.5f}" for v in e])
    msg = f"written {d / 'bands.csv'}: {len(segs)} segments, {len(kd)} k, {nb} bands, E_F={ef:.6f} Ha"
    if vb is not None and cb < nb:
        vbm = max(range(len(eig)), key=lambda k: eig[k][vb])
        cbm = min(range(len(eig)), key=lambda k: eig[k][cb])
        gap = (eig[cbm][cb] - eig[vbm][vb]) * HA_EV
        msg += (f"\n  VBM k#{vbm} ({kd[vbm]:.4f}), CBM k#{cbm} ({kd[cbm]:.4f}), gap along path = {gap:.4f} eV, "
                f"{'direct' if vbm == cbm else 'indirect'} (path only; compare with the SCF-net gap)")
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
