#!/usr/bin/env python3
"""Build references/CRYSTAL23_Manual.md: the CRYSTAL23 User's Manual text (PDF->text, as uploaded by the
user) prefixed with a line-number index, so the manual can be consulted with grep/sed without reading it.

Index blocks (line numbers refer to the OUTPUT file):
  A. Table of contents: section -> printed page -> line
  B. Keywords used by the pipeline -> line of their definition
  C. Page -> line of the page start, for every page (resolves the manual's "see page N" cross-references)

Page detection: the text has a lone page number on its own line at the END of each page; the printed
page numbers equal the physical ones (checked: "1.1 Introduction ... 9" sits between markers 8 and 9).

Usage: build_crystal_manual.py <crystal.md raw> <out.md>
"""
import re
import sys
from pathlib import Path

raw_fn, out_fn = sys.argv[1:3]
L = Path(raw_fn).read_text(errors="replace").splitlines()

# page markers: lone integers that increase by one
ends, p = {}, 0
for i, l in enumerate(L):
    s = l.strip()
    if s.isdigit() and int(s) == p + 1:
        p += 1
        ends[p] = i
npages = p
start = {1: 0}
start.update({k + 1: ends[k] + 1 for k in range(1, npages)})

# TOC: between "Contents" and the end of page 8
toc_from = next(i for i, l in enumerate(L) if l.strip() == "Contents")
toc = []
for l in L[toc_from + 1:ends[8]]:
    s = re.sub(r"\|", " ", l)
    s = re.sub(r"-{3,}", " ", s)
    m = re.match(r"^\s*(.+?)[\s.]*?(\d{1,3})\s*$", s)
    if not m:
        continue
    title = re.sub(r"(\s*\.)+\s*$", "", re.sub(r"\s+", " ", m.group(1))).strip()
    pg = int(m.group(2))
    if title and not title.isdigit() and 1 <= pg <= npages and len(title) > 2:
        toc.append((title, pg))

# keyword definitions: (label, regex, earliest raw line to search from)
KW = [
    ("CRYSTAL geometry input (block 1)", r"Geometry input for crystalline compounds", 300),
    ("EXTERNAL (geometry from fort.34)", r"EXTERNAL,\s*\|\s*\|\s*DLVINPUT", 800),
    ("BASISSET (internal basis library)", r"^2\.2\.2 Basis set input by keywords", 1000),
    ("Basis set input format (standard route)", r"2\.2\.1.*Standard", 300),
    ("ECP / pseudopotential input", r"\| Effective\s*\|.*core\s*\|\s*pseudo-potentials", 4000),
    ("SHRINK (Pack-Monkhorst / Gilat nets)", r"\| SHRINK\s+\| - Pack-Monkhorst", 6000),
    ("NOSYMADA (needed with anisotropic SHRINK)", r"^NOSYMADA$", 6200),
    ("SMEAR", r"^SMEAR$", 6400),
    ("SPINLOCK", r"^SPINLOCK - Spin-polarized", 6500),
    ("TOLDEE (SCF)", r"^TOLDEE - SCF convergence", 6600),
    ("TOLINTEG", r"^TOLINTEG - Truncation", 6600),
    ("FMIXING", r"^FMIXING - Fock/KS", 5600),
    ("LEVSHIFT", r"\| LEVSHIFT\s+\| -\s+\| Eigenvalue", 5000),
    ("BROYDEN / ANDERSON (SCF accelerators)", r"^BROYDEN$", 5000),
    ("GUESSP (density from fort.20)", r"GUESSP", 5000),
    ("BIPOSIZE / EXCHSIZE", r"^BIPOSIZE", 5000),
    ("DFT block: functionals (4.1)", r"\| 4\.1 Choice", 6700),
    ("Global hybrids (B3LYP, PBE0, ...)", r"Global\s*\|?\s*Hybrid", 6800),
    ("Range-separated hybrids (HSE06, HSEsol, ...)", r"Range-Separated", 6900),
    ("SPIN (spin-polarized DFT)", r"^\| SPIN\s+\| unrestricted", 7000),
    ("DFT-D dispersion (4.2)", r"^4\.2 Dispersion correction", 7200),
    ("Integration grids XLGRID/XXLGRID (4.3)", r"^4\.3 Integration grid", 7200),
    ("DFT-D3 (5.1)", r"5\.1\s*\|?\s*DFT-D3", 7500),
    ("Geometry optimization chapter 7", r"7\.1\s*\|?\s*Geometry\s*\|?\s*\|?\s*optimization", 9600),
    ("Default convergence criteria TOLDEG/TOLDEX", r"RMS on\s*\|\s*gradient", 9700),
    ("FULLOPTG / ATOMONLY / CELLONLY / ITATOCEL", r"^\| ATOMONLY", 9800),
    ("TOLDEE / TOLDEG / TOLDEX in OPTGEOM (7.3.5)", r"^TOLDEE threshold on the energy change", 9900),
    ("Trust radius (MAXTRADIUS, TRUSTRADIUS)", r"^\| MAXTRADIUS", 9900),
    ("FINALRUN (integral reclassification)", r"^FINALRUN action", 9900),
    ("MAXCYCLE (OPTGEOM)", r"maximum\s*\|\s*\|\s*number\s*\|\s*of optimization", 10000),
    ("Numerical gradients (SMEAR/conductors)", r"7\.3\.9\s*\|\s*Numerical", 10000),
    ("EXTPRESS (hydrostatic pressure)", r"^EXTPRESS$", 10600),
    ("Integrals classification during opt (7.4.1)", r"^7\.4\.1 On the integrals", 10600),
    ("Restart optimization (7.4.3)", r"7\.4\.3\s*\|\s*Restart", 10600),
    ("Properties: preliminaries / fort.9 (ch. 14)", r"^14\.1 Preliminary|\| 14\.1 Preliminary", 16100),
    ("Properties keyword list (14.2)", r"\| 14\.2 Properties", 16100),
    ("BAND (14.3)", r"\| BAND\s+\|\s+\| - Band", 16300),
    ("k-point labels for BAND, Table 14.1", r"^Table 14\.1", 16500),
    ("k-point labels for BAND, Table 14.2", r"^Table 14\.2", 16500),
    ("DOSS (14.6)", r"\| DOSS\s+\| - Density", 17100),
    ("COOP / COHP (14.7)", r"14\.7\s*\|\s*Crystal", 17200),
    ("NEWK", r"\| NEWK\s+\| - Hamiltonian", 18500),
    ("Mulliken population PPAN", r"PPAN/MULPOPAN - Mulliken", 6000),
    ("Running in parallel (ch. 15)", r"15\.1 Pcrystal and MPPcrystal", 19700),
    ("Basis set chapter 17 (ionic crystals, linear dependence)", r"\| 17\.1\s+\| Molecular", 21000),
    ("k-sampling theory (18.7)", r"18\.7", 21600),
    ("fort.25 / DOSS.DAT / BAND.DAT formats (App. D)", r"^BAND - Band structure$", 24000),
    ("fort.34 format (App. D)", "page:450", 0),
]
found = []
for lab, rx, lo in KW:
    if rx.startswith("page:"):
        found.append((lab, start[int(rx[5:])]))
        continue
    r = re.compile(rx)
    hit = next((i for i in range(lo, len(L)) if r.search(L[i])), None)
    found.append((lab, hit))


def page_of(i):
    for k in range(1, npages + 1):
        if i <= ends[k]:
            return k
    return npages


def header(off):
    h = ["# CRYSTAL23 User's Manual (R. Dovesi et al., October 31, 2023) — indexed text",
         "",
         "> Text extracted from the official PDF (uploaded by the user as `~/work_crystal/crystal.md`).",
         "> Tables come out as broken `|` rows and some words are glued together (`thekeywordFOO`):",
         "> grep case-insensitively and with partial words. NEVER read the whole file: `grep -n -i` then `sed -n 'A,Bp'`.",
         "> Each page ENDS with a line holding only its page number; printed page = physical page, so the",
         "> manual's own \"see page N\" references resolve with index C below.",
         "> Regenerate: `python3 references/build_crystal_manual.py <crystal.md> references/CRYSTAL23_Manual.md`.",
         "",
         "## A. Table of contents (section — page — line)", ""]
    h += [f"- {t} — p.{pg} — L{start[pg] + off + 1}" for t, pg in toc]
    h += ["", "## B. Keywords used by the pipeline (definition line)", ""]
    h += [f"- {lab} — " + (f"L{i + off + 1} (p.{page_of(i)})" if i is not None else "not found: grep it") for lab, i in found]
    h += ["", "## C. Page → first line", ""]
    row = []
    for k in range(1, npages + 1):
        row.append(f"p{k}:L{start[k] + off + 1}")
        if len(row) == 12:
            h.append(" ".join(row)); row = []
    if row:
        h.append(" ".join(row))
    h += ["", "---", "# MANUAL TEXT", ""]
    return h


off = 0
for _ in range(3):  # fixed point: header length does not depend on the digits
    h = header(off)
    off = len(h)
Path(out_fn).write_text("\n".join(header(off) + L) + "\n")
print(f"{out_fn}: {npages} pages, {len(toc)} TOC entries, {sum(i is not None for _, i in found)}/{len(found)} keywords, header {off} lines")
