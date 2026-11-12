#!/usr/bin/env python3
"""scf_monitor.py — detector de charge sloshing / SCF sem progresso a partir do OSZICAR do VASP.

Uso:
  scf_monitor.py --check OSZICAR [--max-steps 60] [--window 20]   # ciclo EM ANDAMENTO (último); exit 3 = sloshing
  scf_monitor.py --calib OSZICAR...                               # estatística offline em OSZICARs prontos

Ciclo = linhas DAV/RMM/SDA/CGA entre duas linhas 'F=' (passo iônico). Critérios (por ciclo):
  (a) teto:      passos eletrônicos > --max-steps
  (b) estagnado: min|dE| dos últimos W passos > --improve x min|dE| dos W anteriores (sem melhora)
  (c) oscila:    >70 % de trocas de sinal de dE nos últimos W passos E min|dE| sem queda de 3x
Passos iniciais não-autoconsistentes (NELMDL) são ignorados: janelas começam após --skip passos.
Limiares: calibrados em 2026-11-12 (ver gotchas.md do vasp-pipeline).
"""
import argparse, re, sys

LINE = re.compile(r"^\s*(DAV|RMM|SDA|CGA|DIA|CHI|EDI|BRM):\s+(\d+)\s+(\S+)\s+(\S+)")


def cycles(path):
    """Lista de ciclos; cada ciclo = (lista de dE, convergiu?)."""
    out, cur = [], []
    with open(path, errors="replace") as fh:
        for ln in fh:
            m = LINE.match(ln)
            if m:
                try:
                    cur.append(float(m.group(4)))
                except ValueError:
                    pass
            elif "F=" in ln:
                out.append((cur, True)); cur = []
    if cur:
        out.append((cur, False))
    return out


def first_trigger(dE, max_steps=60, W=20, improve=0.1, skip=12, flip=0.7):
    """Índice (1-based) do primeiro passo em que algum critério dispara, e qual; None se nenhum."""
    for k in range(1, len(dE) + 1):
        if k > max_steps:
            return k, "a:teto"
        if k < skip + 2 * W:
            continue
        last = [abs(x) for x in dE[k - W:k]]
        prev = [abs(x) for x in dE[k - 2 * W:k - W]]
        ml, mp = min(last), min(prev)
        if mp > 0 and ml > improve * mp:
            return k, "b:estagnado"
        sg = [dE[i] > 0 for i in range(k - W, k)]
        flips = sum(sg[i] != sg[i - 1] for i in range(1, W)) / (W - 1)
        if flips > flip and mp > 0 and ml > mp / 3:
            return k, "c:oscila"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--check"); ap.add_argument("--calib", action="store_true")
    ap.add_argument("--max-steps", type=int, default=60)
    ap.add_argument("--window", type=int, default=20)
    ap.add_argument("--improve", type=float, default=0.1)
    ap.add_argument("--skip", type=int, default=12)
    a = ap.parse_args()
    kw = dict(max_steps=a.max_steps, W=a.window, improve=a.improve, skip=a.skip)
    if a.check:
        cs = cycles(a.check)
        if not cs or cs[-1][1]:
            print("ok: nenhum ciclo em andamento"); return 0
        t = first_trigger(cs[-1][0], **kw)
        if t:
            print(f"SLOSH {t[1]} no passo eletrônico {t[0]} (ciclo com {len(cs[-1][0])} passos)"); return 3
        print(f"ok: {len(cs[-1][0])} passos no ciclo atual"); return 0
    if a.calib:
        agg = {}
        for f in a.files:
            ph = f.split("/")[0]
            for dE, done in cycles(f):
                if not done or len(dE) < 3:
                    continue
                t = first_trigger(dE, **kw)
                s = agg.setdefault(ph, dict(n=0, trig=0, kinds={}, steps=[]))
                s["n"] += 1; s["steps"].append(len(dE))
                if t:
                    s["trig"] += 1; s["kinds"][t[1]] = s["kinds"].get(t[1], 0) + 1
        print(f"limiares: max_steps={a.max_steps} W={a.window} improve={a.improve} skip={a.skip}")
        print("fase  ciclos_convergidos  disparariam_antes_de_convergir  (tipos)  passos max")
        for ph, s in sorted(agg.items()):
            print(f"{ph:10s} {s['n']:5d} {s['trig']:5d} {s['kinds']} max={max(s['steps'])}")
        return 0
    ap.print_help(); return 1


if __name__ == "__main__":
    sys.exit(main())
