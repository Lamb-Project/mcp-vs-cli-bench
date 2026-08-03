#!/usr/bin/env bash
# Render paper.md to a print-ready PDF.
#
# Typst rather than LaTeX: it handles the wide results table without manual
# column tuning, and the figures are already vector PDFs so they drop in
# unscaled. Requires pandoc >= 3 with the typst writer.
set -euo pipefail

cd "$(dirname "$0")"

command -v pandoc >/dev/null || { echo "pandoc not found" >&2; exit 1; }

# Figures must exist before rendering; a missing figure becomes a silent gap.
missing=0
for f in tokens toolcalls completion cost; do
    [ -f "figures/${f}.pdf" ] || { echo "missing figures/${f}.pdf" >&2; missing=1; }
done
[ "$missing" -eq 0 ] || { echo "run: python -m bench.analyze" >&2; exit 1; }

pandoc paper.md \
    --from=markdown+pipe_tables+footnotes+implicit_figures \
    --pdf-engine=typst \
    --variable mainfont="Palatino" \
    --variable fontsize=10pt \
    --variable papersize=us-letter \
    --variable margin-x=2cm \
    --variable margin-y=2cm \
    --output=paper.pdf

echo "wrote $(pwd)/paper.pdf"
