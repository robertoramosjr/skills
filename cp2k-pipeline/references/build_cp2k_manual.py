#!/usr/bin/env python3
"""Compila o manual do CP2K (docs/ do GitHub + cp2k_input.xml) em UM .md.

uso: build_cp2k_manual.py <repo/docs> <cp2k_input.xml> <saida.md> <commit> <data>
Parte I   = narrativa (docs/**/*.md, ordem do toctree, MyST limpo)
Parte II  = referência de input (seções/keywords do XML, subárvores idênticas deduplicadas)
Parte III = bibliografia e unidades
Apêndice  = exemplos .inp do manual
"""
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

docs, xml_fn, out_fn, commit, today = sys.argv[1:6]
docs = Path(docs)

# ----------------------------------------------------------------------------- Parte I
FENCE = re.compile(r"^(\s*)(`{3,}|:{3,})\{([A-Za-z0-9_-]+)\}\s*(.*)$")
DROP = {"toctree", "image", "figure", "rubric", "container", "youtube"}


def split_block(lines, i, fence_chars):
    """devolve (corpo, índice após o fechamento) do bloco que abre em lines[i]."""
    ch, n = fence_chars[0], len(fence_chars)
    close = re.compile(r"^\s*" + re.escape(ch) + "{" + str(n) + r",}\s*$")
    j = i + 1
    body = []
    while j < len(lines) and not close.match(lines[j]):
        body.append(lines[j])
        j += 1
    return body, j + 1


def clean_inline(s):
    s = re.sub(r"\{ref\}`([^`<]*?)\s*<[^`>]*>`", r"\1", s)
    s = re.sub(r"\{math\}`([^`]*)`", r"$\1$", s)
    s = re.sub(r"\{[A-Za-z]+\}`([^`]*)`", r"`\1`", s)
    s = re.sub(r"\[\]\(project:[^)]*\)", "", s)
    s = re.sub(r"\[([^\]]+)\]\(project:[^)]*\)", r"\1", s)
    s = re.sub(r"\[\]\(#([^)]+)\)", r"(\1)", s)
    s = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"[figura omitida: \2 — \1]", s)
    s = re.sub(r"<small>\[\[Edit on GitHub\][^<]*</small>", "", s)
    return s


def process(lines):
    out, i = [], 0
    in_code = False
    while i < len(lines):
        ln = lines[i]
        m = FENCE.match(ln)
        if not in_code and m:
            name = m.group(3)
            body, i = split_block(lines, i, m.group(2))
            if name in DROP:
                if name == "youtube":
                    out.append(f"[video youtube: {m.group(4).strip()}]")
                continue
            if name == "glossary":
                out.extend(process(body))
            else:
                out.append(f"**{name.upper()}:**")
                out.extend(process(body))
            continue
        if re.match(r"^\s*(`{3,}|~{3,})", ln):
            in_code = not in_code
            out.append(ln)
        elif in_code:
            out.append(ln)
        elif re.match(r"^\([^)]+\)=\s*$", ln):
            pass
        else:
            out.append(clean_inline(ln))
        i += 1
    return out


def demote(lines, by):
    out, in_code = [], False
    for ln in lines:
        if re.match(r"^\s*(`{3,}|~{3,})", ln):
            in_code = not in_code
        if not in_code:
            m = re.match(r"^(#{1,6})(\s.*)$", ln)
            if m:
                ln = "#" * min(6, len(m.group(1)) + by) + m.group(2)
        out.append(ln)
    return out


def toctree_order(rel, seen, order):
    p = docs / rel
    if rel in seen or not p.exists():
        return
    seen.add(rel)
    order.append(rel)
    txt = p.read_text(encoding="utf-8")
    for blk in re.finditer(r"`{3,}\{toctree\}(.*?)`{3,}", txt, re.S):
        for ln in blk.group(1).splitlines():
            ln = ln.strip()
            if not ln or ln.startswith(":") or ln.startswith("---") or ln in ("caption:", "titlesonly:", "maxdepth: 1") or re.match(r"^\w+:", ln):
                continue
            tgt = re.sub(r"^.*<(.*)>$", r"\1", ln)
            if tgt.startswith("http") or tgt == "CP2K_INPUT":
                continue
            cand = (Path(rel).parent / (tgt if tgt.endswith(".md") else tgt + ".md")).as_posix()
            toctree_order(cand, seen, order)


order, seen = [], set()
toctree_order("index.md", seen, order)
skip = {"index.md", "README.md", "versions.md"}
rest = sorted(
    p.relative_to(docs).as_posix()
    for p in docs.rglob("*.md")
    if not p.relative_to(docs).as_posix().startswith("_") and p.relative_to(docs).as_posix() not in seen
)
rest = [r for r in rest if r not in skip]
# changelog por último
files = [f for f in order if f not in skip] + [r for r in rest if r != "changelog.md"] + (["changelog.md"] if "changelog.md" in rest else [])

part1 = []  # (rel, lines)
for rel in files:
    txt = (docs / rel).read_text(encoding="utf-8")
    body = process(txt.splitlines())
    body = demote(body, 2)
    part1.append((rel, body))

# ----------------------------------------------------------------------------- Parte II
root = ET.parse(xml_fn).getroot()
ver = (root.findtext("CP2K_VERSION") or "").strip()
rev = (root.findtext("COMPILE_REVISION") or "").strip()
comp = (root.findtext("COMPILE_DATE") or "").strip()


def T(e, tag):
    x = e.find(tag)
    return (x.text or "").strip() if x is not None else ""


def kw_line(k, sec=False):
    names = [n for n in k.findall("NAME")]
    dn = next((n.text for n in names if n.get("type") == "default"), "?")
    al = [n.text for n in names if n.get("type") == "alias"]
    dt = k.find("DATA_TYPE")
    kind = dt.get("kind")
    nv = T(dt, "N_VAR")
    meta = [kind + (f"[{nv}]" if nv not in ("", "1") else "")]
    dv = T(k, "DEFAULT_VALUE")
    if dv:
        meta.append(f"default={dv}")
    du = T(k, "DEFAULT_UNIT")
    if du:
        meta.append(f"unit={du}")
    lv = T(k, "LONE_KEYWORD_VALUE")
    if lv:
        meta.append(f"lone={lv}")
    if k.get("repeats") == "yes":
        meta.append("repeatable")
    if k.find("DEPRECATION_NOTICE") is not None:
        meta.append("DEPRECATED: " + T(k, "DEPRECATION_NOTICE"))
    head = f"- `{dn}`" + (f" (alias {', '.join(al)})" if al else "") + " [" + "; ".join(meta) + "]"
    d = T(k, "DESCRIPTION")
    if d:
        d = d.replace("\n", "\n  ")
        head += " — " + d
    en = dt.find("ENUMERATION")
    if en is not None:
        items = []
        for it in en.findall("ITEM"):
            nm, ds = T(it, "NAME"), " ".join(T(it, "DESCRIPTION").split())
            items.append(f"`{nm}`" + (f": {ds}" if ds else ""))
        head += "\n  - opções: " + "; ".join(items)
    refs = [T(r, "NAME") for r in k.findall("REFERENCE")]
    if refs:
        head += "\n  - refs: " + ", ".join(refs)
    return head


def sig(s):
    """assinatura do conteúdo da seção (sem LOCATION), recursiva."""
    h = hashlib.sha1()

    def walk(e):
        h.update(e.tag.encode())
        h.update((e.text or "").strip().encode())
        for k, v in sorted(e.attrib.items()):
            h.update(f"{k}={v}".encode())
        for c in e:
            if c.tag == "LOCATION":
                continue
            walk(c)

    walk(s)
    return h.hexdigest()


seen_sig = {}
part2 = []
nsec = nkw = ndup = 0


def emit(s, path):
    global nsec, nkw, ndup
    name = T(s, "NAME")
    here = path + [name]
    p = "/".join("&" + x for x in here)
    kws = [k for k in s.findall("KEYWORD") if k.get("removed") != "yes"]
    dkw = s.find("DEFAULT_KEYWORD")
    subs = s.findall("SECTION")
    sg = sig(s)
    lvl = min(6, len(here) + 2)
    part2.append("")
    part2.append("#" * lvl + f" {p}")
    if sg in seen_sig and (kws or subs):
        ndup += 1
        part2.append(f"(conteúdo idêntico, incluindo subseções, a `{seen_sig[sg]}` — ver lá)")
        return
    seen_sig[sg] = p
    nsec += 1
    d = T(s, "DESCRIPTION")
    if d:
        part2.append(d)
    flags = []
    if s.get("repeats") == "yes":
        flags.append("seção repetível")
    if s.find("DEPRECATION_NOTICE") is not None:
        flags.append("DEPRECATED: " + T(s, "DEPRECATION_NOTICE"))
    refs = [T(r, "NAME") for r in s.findall("REFERENCE")]
    if refs:
        flags.append("refs: " + ", ".join(refs))
    if flags:
        part2.append("_" + "; ".join(flags) + "_")
    sp = s.find("SECTION_PARAMETERS")
    if sp is not None:
        part2.append("Parâmetro da seção (`&" + name + " <valor>`):")
        part2.append(kw_line(sp))
    if dkw is not None:
        part2.append("Keyword livre (formato do bloco):")
        part2.append(kw_line(dkw))
    if subs:
        part2.append("Subseções: " + ", ".join("&" + T(x, "NAME") for x in subs if x.get("removed") != "yes"))
    if kws:
        part2.append("")
        for k in kws:
            part2.append(kw_line(k))
            nkw += 1
    for c in subs:
        if c.get("removed") != "yes":
            emit(c, here)


for top in root.findall("SECTION"):
    emit(top, [])

# ----------------------------------------------------------------------------- Parte III
part3 = ["", "## Bibliografia (chaves citadas em `refs:`)", ""]
refs = sorted(root.findall("REFERENCE"), key=lambda r: T(r, "NAME") or r.get("key", ""))
for r in refs:
    au = "; ".join(T(a, "") if False else (a.text or "").strip() for a in r.findall("AUTHOR"))
    part3.append(
        f"- **{r.get('key')}** — {au} ({T(r,'YEAR')}). {T(r,'TITLE')}. {T(r,'SOURCE')} {T(r,'VOLUME')} {T(r,'PAGES')}"
        + (f". doi:{T(r,'DOI')}" if T(r, "DOI") else "")
    )
part3 += ["", "## Unidades aceitas (UNIT_KIND)", ""]
for u in root.findall("UNIT_KIND"):
    part3.append(f"- **{u.get('name')}**: " + ", ".join((x.text or "").strip() for x in u.findall("UNIT")))

# ----------------------------------------------------------------------------- Apêndice
part4 = []
for p in sorted(docs.rglob("*.inp")):
    part4 += ["", f"### {p.relative_to(docs).as_posix()}", "", "```", p.read_text(encoding="utf-8").rstrip(), "```"]

# ----------------------------------------------------------------------------- montagem
part2 = "\n".join(part2).split("\n")
part3 = "\n".join(part3).split("\n")
part4 = "\n".join(part4).split("\n")
head = [
    "# CP2K — Manual compilado (narrativa + referência de input)",
    "",
    f"- Fonte narrativa: https://github.com/cp2k/cp2k/tree/master/docs (commit `{commit}`, {today})",
    f"- Referência de input: gerada de `cp2k_input.xml` do manual oficial (trunk): {ver}, rev {rev}, compilado {comp}",
    "- Conversão: MyST limpo (toctree/figuras removidos, figuras viram `[figura omitida: ...]`); referência de input compactada",
    "  (1 linha por keyword; subárvores idênticas, ex. `XC_FUNCTIONAL` replicado em dezenas de lugares, aparecem 1 vez e as demais apontam para a primeira).",
    "- Não incluídos: `index.md`, `README.md`, `versions.md` (só toctree/instruções de build do site).",
    "- Versões em uso: access = cp2k/2026.1, coaraci = 2025.1 psmp / 2026.2 ssmp. Keyword que não existir na sua versão: checar `cp2k --xml`/o `.out`.",
    "- Uso: `grep -n -i` neste arquivo (nunca ler inteiro). Parte II: procurar `^#+ &FORCE_EVAL/&DFT/&QS` ou ``^- `KEYWORD` ``.",
    "",
]
body = []
body.append("# PARTE I — Manual (narrativa)")
index_i = []
for rel, lines in part1:
    body.append("")
    index_i.append((rel, len(body)))
    body.append(f"## [[{rel}]]")
    body.append("")
    body.extend(lines)
body += ["", "# PARTE II — Referência de input (seções e keywords)", f"_Gerada de {ver}, rev {rev}. Formato: `NOME` [tipo; default; unit; lone; repeatable] — descrição._"]
p2_start = len(body)
body += part2
body += ["", "# PARTE III — Bibliografia e unidades"] + part3
body += ["", "# APÊNDICE — Exemplos .inp do manual"] + part4

# índice com números de linha reais
toc = ["## Índice (linha no arquivo)", ""]
off = len(head) + 1 + 2 + len(files) + 6 + 12  # folga; recalculada abaixo
text_wo_toc = head + body
# 2 passes: calcular tamanho do toc
toc_len = len(toc) + len(files) + 1 + 1 + 4 + 8  # mesma conta do bloco final
final_toc = None
for _ in range(3):
    base = len(head) + toc_len
    lines_toc = ["## Índice (linha no arquivo)", "", "Parte I:"]
    for rel, ln in index_i:
        lines_toc.append(f"- L{base + ln + 1}: {rel}")
    sec_idx = [(i, l) for i, l in enumerate(part2) if re.match(r"^#{3} &", l)]
    lines_toc += ["", "Parte II (seções de 1º nível):"]
    for i, l in sec_idx:
        lines_toc.append(f"- L{base + p2_start + i + 1}: {l.lstrip('# ')}")
    lines_toc += ["", "Parte III e Apêndice: ver cabeçalhos `# PARTE III` e `# APÊNDICE`.", ""]
    if len(lines_toc) == toc_len:
        break
    toc_len = len(lines_toc)
final = head + lines_toc + body
Path(out_fn).write_text("\n".join(final) + "\n", encoding="utf-8")
print(f"Parte I: {len(part1)} arquivos | Parte II: {nsec} seções únicas, {ndup} duplicadas->ponteiro, {nkw} keywords | refs: {len(refs)} | linhas: {len(final)}")
