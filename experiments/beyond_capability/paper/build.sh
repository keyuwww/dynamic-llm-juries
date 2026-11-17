#!/bin/sh
# Rebuild every number, table and figure of the paper from the stored results, then compile main.pdf.
#   sh experiments/beyond_capability/paper/build.sh
set -e
cd "$(dirname "$0")/.."
python3 paper_analysis.py > /dev/null      # out_paper/results.json, results.md
python3 -c "import json, paper_analysis as P, paper_data as D; json.dump(P.authorship(D.pool_sets()), open('out_paper/authorship.json', 'w'), indent=1)"
python3 paper_tables.py                    # paper/numbers.tex, tab_*.tex
python3 paper_figures.py                   # paper/fig_*.pdf
cd paper
pdflatex -interaction=nonstopmode main.tex > /dev/null
bibtex main > /dev/null
pdflatex -interaction=nonstopmode main.tex > /dev/null
pdflatex -interaction=nonstopmode main.tex > build.log
grep -E "^!|undefined" build.log || true
grep -c "??" main.tex numbers.tex > /dev/null || true
python3 -c "from pypdf import PdfReader; print(len(PdfReader('main.pdf').pages), 'pages')"
