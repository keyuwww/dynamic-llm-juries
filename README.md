# Grading Like the Experts

Five LLM judges graded 799 BFF-Bench finance answers twice: with a standard grading prompt, and with the five rules Kensho's experts used to make the labels. This folder holds the experiment, every verdict, the results and the findings page. The notebook grades and scores, its output sits in `results/`, and [results.md](results.md) sums up what the results show.

| Path | What it is |
|---|---|
| [results.md](results.md) | The findings, one question per section, with tables and charts |
| [notebook/grading_like_experts.ipynb](notebook/grading_like_experts.ipynb) | The experiment, with its outputs saved. It builds the 799 answers, grades them, scores each judge and writes `results/` |
| [prompts/](prompts) | The three system prompts and the user message, word for word |
| [runs/](runs) | Every verdict, one file per judge and prompt, named `<judge>__<prompt>.jsonl` |
| [results/](results) | The three tables as CSVs, and the four charts in `figures/` |
| [page/](page) | The findings page. `findings.py` is the marimo notebook and `index.html` its export. GitHub shows HTML as text, so download `index.html` and open it in a browser |
| [lib/](lib) | `juries.py` computes every number for both the notebook and the page. `charts.py` and `nbkit.py` draw the page |
| [data/](data) | Kensho's VERDICTS and BFF-Bench data, and a hand reading of gpt-oss-120b's rejections. [data/README.md](data/README.md) gives the sources and licenses |

The prompts are `STD`, the standard prompt, `GUIDE`, the experts' five rules, and `GUIDE_NO2`, the rules without rule 2 ("steps disagree: incorrect"). Only the two gpt-oss judges were graded with `GUIDE_NO2`. The verdicts are from Oct 15 to 17, 2026.

## Columns

- `results_by_judge_prompt.csv` has one row per judge, prompt and group of answers. `answers` is all answers, or one group by how the experts voted: all 3 agree, 2 agree + 1 not sure, or a 2-1 split.
- `kappa`, `kappa_lo` and `kappa_hi` are Cohen's κ with the expert labels and its 95% interval. `false_accept` is the share of wrong answers called correct, and `false_reject` the share of correct answers called wrong. `parsed` and `cost_per_1000` are filled for all answers only, and cost is blank for the self-hosted gpt-oss judges.
- `prompt_differences.csv` has the change in κ between two prompts on the same answers, `delta_kappa`, with its 95% interval from `lo` to `hi`. `GUIDE-STD` is the rules minus the standard prompt.
- `answers_and_labels.csv` lists the 799 answers, their conversation and turn, how the three experts voted, and `label_correct`, the majority label, 1 for correct.
- In `runs/`, each row is one verdict. `verdict` is 1 for correct, 0 for incorrect and -1 for no verdict, which counts as wrong. `text` is the last 4,000 characters of the judge's output.

## Rerun

```
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace notebook/grading_like_experts.ipynb
marimo export html page/findings.py -o page/index.html --no-include-code -f
```

The notebook reuses every verdict in `runs/` and grades only what is missing. As shipped nothing is missing, so it makes no API calls and needs no keys, and it rewrites `results/` and the charts. To grade more, copy `.env.example` to `.env` in this folder and add your keys. The guardrails cap spend at $2 on OpenRouter, $10 on OpenAI and $90 on Modal. A regrade can differ a little, because API hosts are not deterministic even at temperature 0: qwen3.7-flash changed 7.0% of its verdicts between two identical runs.

The page and the notebook read the same numbers from `lib/juries.py`, which caches them in `.cache/` until a run file changes.
