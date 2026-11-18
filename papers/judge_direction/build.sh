#!/bin/sh
# Rebuild every number, table and figure of the paper from the stored results, then compile main.pdf.
#   sh papers/judge_direction/build.sh
# Analysis code and results live in experiments/beyond_capability/.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../../experiments/beyond_capability"
python3 paper_analysis.py > /dev/null      # out_paper/results.json, results.md
python3 -c "import json, paper_analysis as P, paper_data as D; json.dump(P.authorship(D.pool_sets()), open('out_paper/authorship.json', 'w'), indent=1)"
python3 paper_authorship.py > /dev/null  # out_paper/authorship_check.json (authorship_dir.json comes from authorship_dir_modal.py)
python3 paper_tables.py                    # papers/judge_direction/numbers.tex, tab_*.tex
python3 paper_figures.py                   # papers/judge_direction/fig_*.pdf
cd "$HERE"
pdflatex -interaction=nonstopmode main.tex > /dev/null
bibtex main > /dev/null
pdflatex -interaction=nonstopmode main.tex > /dev/null
pdflatex -interaction=nonstopmode main.tex > build.log
grep -E "^!|undefined" build.log || true
python3 -c "from pypdf import PdfReader; print(len(PdfReader('main.pdf').pages), 'pages')"
