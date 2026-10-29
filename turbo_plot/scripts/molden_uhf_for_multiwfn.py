#!/usr/bin/env python3
"""Open-shell (UHF/UKS) TURBOMOLE molden -> spherical molden_new.molden for Multiwfn, virtuals kept.

tm2molden writes alpha and beta MOs interleaved by energy; molden2aim drops Occup=0 orbitals and
expects one alpha block followed by one beta block. This script (1) regroups alpha then beta,
(2) marks every MO as occupied (1.0) so molden2aim keeps the virtuals, (3) runs molden2aim,
(4) restores Occup = 1 for the lowest NA alpha and NB beta orbitals and 0 above.
Closed-shell molecules: use molden_for_multiwfn.sh instead.

Usage:
    python molden_uhf_for_multiwfn.py --molden ../mol.molden --nalpha 168 --nbeta 167
Run inside the working directory (writes molden.input, m2a.ini, molden_new.molden).
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def split_mos(text):
    """Return (header, list of MO blocks) from a molden string."""
    head, body = text.split("[MO]", 1)
    blocks = re.split(r"(?=^\s*Sym=)", body, flags=re.M)
    return head, [b for b in blocks if b.strip()]


def spin_of(block):
    return re.search(r"Spin=\s*(\w+)", block).group(1).lower()


def set_occ(block, value):
    return re.sub(r"Occup=\s*[-\d.EeDd+]+", f"Occup= {value:.8f}", block)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--molden", required=True, type=Path, help="molden from tm2molden (UHF)")
    p.add_argument("--nalpha", required=True, type=int, help="number of occupied alpha MOs")
    p.add_argument("--nbeta", required=True, type=int, help="number of occupied beta MOs")
    p.add_argument("--molden2aim", default=os.path.expanduser("~/local_bin/molden2aim.exe"))
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    head, blocks = split_mos(a.molden.read_text())
    alpha = [b for b in blocks if spin_of(b) == "alpha"]
    beta = [b for b in blocks if spin_of(b) == "beta"]
    print(f"alpha MOs: {len(alpha)}  beta MOs: {len(beta)}")
    prepared = "[Program] turbomole\n" + head + "[MO]\n" + "".join(set_occ(b, 1.0) for b in alpha + beta)
    Path("molden.input").write_text(prepared)
    Path("m2a.ini").write_text("carsph=1\n")
    subprocess.run(f'printf "No\\n" | {a.molden2aim} -i molden.input > m2a.log 2>&1',
                   shell=True, check=False)  # exits non-zero at the final prompt
    head2, blocks2 = split_mos(Path("molden_new.molden").read_text())
    counts = {"alpha": 0, "beta": 0}
    limits = {"alpha": a.nalpha, "beta": a.nbeta}
    out = []
    for b in blocks2:
        s = spin_of(b)
        counts[s] += 1
        out.append(set_occ(b, 1.0 if counts[s] <= limits[s] else 0.0))
    Path("molden_new.molden").write_text(head2 + "[MO]\n" + "".join(out))
    print(f"molden_new.molden: alpha {counts['alpha']} (occ {a.nalpha}), beta {counts['beta']} (occ {a.nbeta})")
    for f in Path(".").glob("*123456789.tmp"):
        f.unlink()
    for f in ("molden.input", "molden.wfn"):
        Path(f).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
