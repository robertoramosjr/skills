#!/usr/bin/env bash
# texbuild.sh — compila papers revtex/LaTeX com o ambiente conda `writing_env`
# (tectonic + ghostscript + poppler), sem TeX Live no sistema.
#
# Uso:  texbuild.sh <arquivo.tex> [<outro.tex> ...] [--png] [--dpi N]
#   - copia a pasta do .tex (sem old/ e _build/) para <pasta>/_build/
#   - converte toda figura .eps em .pdf (ghostscript, -dEPSCrop) e troca
#     \includegraphics{...eps} por ...pdf SÓ na cópia (o .tex original não muda)
#   - compila com tectonic (roda bibtex sozinho); PDF em <pasta>/_build/
#   - lista referências/citações indefinidas e overfull boxes
#   - --png: renderiza as páginas em _build/pages_<stem>/ (pdftoppm, 60 dpi padrão)
#
# Recriar o ambiente:
#   conda create -y -n writing_env -c conda-forge tectonic ghostscript poppler python=3.12
# Primeira compilação baixa os pacotes do TeX Live para ~/.cache/Tectonic (precisa de internet).
set -euo pipefail

ENV=writing_env
PNG=0; DPI=60; FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --png) PNG=1 ;;
    --dpi) DPI="$2"; shift ;;
    -h|--help) sed -n 2,16p "$0"; exit 0 ;;
    *) FILES+=("$1") ;;
  esac
  shift
done
[ ${#FILES[@]} -gt 0 ] || { echo "uso: $0 arquivo.tex [--png]"; exit 1; }

if command -v tectonic >/dev/null 2>&1 && command -v gs >/dev/null 2>&1; then
  RUN=""
else
  RUN="conda run --no-capture-output -n $ENV"
fi

rc=0
for TEX in "${FILES[@]}"; do
  TEX=$(readlink -f "$TEX"); SRC=$(dirname "$TEX"); STEM=$(basename "$TEX" .tex)
  B="$SRC/_build"; mkdir -p "$B"
  # cópia da pasta do paper (sem versões antigas nem builds)
  (cd "$SRC" && tar --exclude=./old --exclude=./_build -cf - .) | (cd "$B" && tar -xf -)
  # EPS -> PDF (só se o PDF não existir ou estiver mais velho)
  while IFS= read -r -d '' e; do
    p="${e%.eps}.pdf"
    if [ ! -f "$p" ] || [ "$e" -nt "$p" ]; then
      $RUN gs -q -dNOPAUSE -dBATCH -dSAFER -dEPSCrop -sDEVICE=pdfwrite -sOutputFile="$p" "$e"
    fi
  done < <(find "$B" -name '*.eps' -print0)
  sed -i -E 's/(\\includegraphics(\[[^]]*\])?\{[^}]*)\.eps\}/\1.pdf}/g' "$B/$STEM.tex"
  echo "== $STEM: compilando em $B"
  if (cd "$B" && $RUN tectonic -X compile --keep-logs "$STEM.tex" > "$STEM.tectonic.out" 2>&1); then
    echo "   OK -> $B/$STEM.pdf ($(cd "$B" && $RUN pdfinfo "$STEM.pdf" | awk '/^Pages/{print $2}') páginas)"
  else
    echo "   FALHOU — erros:"; grep -E '^error' "$B/$STEM.tectonic.out" | head -20 | sed 's/^/   /'; rc=1; continue
  fi
  LOG="$B/$STEM.log"
  grep -E "Reference .* undefined|Citation .* undefined" "$LOG" | sed 's/^/   indefinido: /' | sort -u || true
  grep -E "Overfull \\\\hbox" "$LOG" | sed 's/^/   /' | sort -u | head -10 || true
  if [ $PNG = 1 ]; then
    rm -rf "$B/pages_$STEM"; mkdir -p "$B/pages_$STEM"
    (cd "$B" && $RUN pdftoppm -r "$DPI" -png "$STEM.pdf" "pages_$STEM/p")
    echo "   páginas: $B/pages_$STEM/"
  fi
done
exit $rc
