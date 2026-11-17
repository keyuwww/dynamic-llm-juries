# Paper: Small LLM Judges Know More Than They Say, Mostly About Who Wrote the Answer

ACL long-paper draft (review mode). `sh build.sh` rebuilds every number, table and figure from stored results and compiles `main.pdf`.

## Where each result comes from

| Result | Produced by | Stored in |
|---|---|---|
| Verdict, push test, stretch (main answer pools) | `azure/pair_pipeline.py` via `allpairs_modal.py` (H100) | `out_allpairs/<judge>_<bench>/final_*.jsonl`, `choice_*.json` |
| Direction position per answer (main pools) | `direct_readout_modal.py` (CPU, from stored hidden states) | `out_allpairs/*/direct_*.json` |
| Same-model sets, Qwen3.5-4B answers | `sm_build_items.py`, `sm_build_bbeh.py`; judged by `allpairs_modal.py --phase extra` / `extra_direct` | `out_allpairs/*/extra_*.jsonl`, `xdirect_*.jsonl` |
| Same-model sets, OLMo-2-7B answers | `sm2_gen_modal.py` (vLLM), GLM grading (`modal_app.py --phase egrade`), `sm_build_items.py olmo2-7b sm2`, `allpairs_modal.py --phase sm2` | `out_allpairs/*/sm2extra_*.jsonl` |
| Reason-first verdicts | `cot_modal.py` (vLLM) | `out_allpairs/*/cot_{main,sm,sm2}.jsonl` |
| Gap over 20 splits | `allpairs_modal.py --phase splits` | `out_allpairs/knows_splits.json` |
| All comparisons | `paper_data.py`, `paper_analysis.py` | `out_paper/results.json`, `results.md`, `authorship.json` |
| Numbers, tables, figures | `paper_tables.py`, `paper_figures.py` | `paper/numbers.tex`, `tab_*.tex`, `fig_*.pdf` |

Every number in the text is a `\R{key}` lookup into `numbers.tex`; an unknown key prints **??**.

`refs.bib` entries were checked against arXiv / venue pages (notes in `related_notes.md`).
