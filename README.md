# Self-Agreement

Without an answer key, a juror's agreement with itself picks which of its grades to trust better than self-solve, the check of whether it can solve the question. It scores higher than self-solve for all four jurors, by +0.074 to +0.150 in Cohen's κ, with the interval above 0 for three. Inside a jury the two signals tie, and no jury beats the best single judge. The main limit is self-solve's grader, which missed its 0.80 bar. This folder holds the experiment, every model output, the results and the findings page. The notebook scores every juror and jury, its output sits in `results/`, and [results.md](results.md) sums up what the results show.

| Path | What it is |
|---|---|
| [results.md](results.md) | The findings, one question per section, with tables and charts |
| [notebook/self_agreement.ipynb](notebook/self_agreement.ipynb) | The experiment, with its outputs saved. It checks that every model output is in `runs/`, scores every juror and jury, and writes `results/` and the charts |
| [prompts/](prompts) | Every instruction and message the models got, word for word |
| [runs/](runs) | Every model output, one file per model and step, from the screening to the repeat reads. `steps.csv` lists the steps |
| [results/](results) | The main tables as CSVs and the four charts in `figures/`. `checks/` holds the supporting checks and `per_answer/` one row per answer |
| [page/](page) | The findings page. `findings.py` is the marimo notebook and `index.html` its export. GitHub shows HTML as text, so download `index.html` and open it in a browser while online, as it loads marimo's viewer from the web |
| [lib/](lib) | `self_agreement.py` computes every number and `figures.py` draws the charts. `run_stages.py` fills missing rows on Tinker or Modal. `charts.py` and `nbkit.py` draw the page |
| [data/](data) | Kensho's VERDICTS, BFF-Bench and CMTBench data. [data/README.md](data/README.md) gives the sources and licenses |

The four jurors are gpt-oss-20b, gpt-oss-120b, qwen3.6-35b and nemotron-3-super. They graded 544 answers with no reference, 316 to BFF-Bench finance questions and 228 to Kensho's corrected MT-Bench math and reasoning questions. Each juror read every answer twice: a gut read gives a one-token verdict, and a reasoned read gives a verdict after reasoning. A juror agrees with itself when the two give the same verdict. Each juror also answered every question, and the grader, qwen3.5-397b, judged those answers against the expert reference. Self-solve, from Kensho's paper No Free Labels, trusts a juror only where it solved the question. Three experts labelled each answer, and every result is agreement with their majority label. The add-on fifth juror, gpt-oss-safeguard-20b, ran on Modal and every other model on Tinker, all on Oct 24, 2026.

## Columns

- `results_by_rule.csv` scores each jury (`jurors`), `rule`, single `juror` and `answer_set`. `kappa` is Cohen's κ with the experts' majority label, with its 95% interval from `kappa_lo` to `kappa_hi`. In `jurors`, 4 is the main result, 3 leaves out qwen3.6-35b and 5 adds gpt-oss-safeguard-20b.
- `contrasts.csv` has the `difference` in κ, `rule` minus `minus` on the same answers, with its interval from `lo` to `hi`.
- `matched_coverage.csv` has one row per juror. `answers_kept` is how many answers each routing keeps, and the `kappa_` columns score its reasoned read on the answers that self-solve, self-agreement and random draws keep.
- `decisions.csv` has each rule set before the run, its `outcome`, the numbers it `reads` and what it `needs`.
- In `runs/`, each row is one model output, byte for byte. The juror or grader field holds a short code, and `MODELS` in `lib/self_agreement.py` maps each to its name. `v` is the verdict: 1 correct, 0 incorrect and -1 none, which counts as a reject.

[results.md](results.md#terms) defines the reads, the signals and the juries.

## Rerun

```
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace notebook/self_agreement.ipynb --ExecutePreprocessor.timeout=1500 --ExecutePreprocessor.record_timing=False
marimo export html page/findings.py -o page/index.html --no-include-code -f
```

The notebook reuses every row in `runs/` and calls a model only for a missing row. As shipped nothing is missing, so it makes no API calls and needs no keys. It rewrites `results/` and the charts in a little over two minutes. Export the page after the notebook, as it reads `results/`, and keep every file in `runs/` where it is.

To fill missing rows, copy `.env.example` to `.env` in this folder and add your `TINKER_API_KEY`. For the add-on juror, also set `SAFEGUARD = True` in the notebook and add your Modal tokens. A refilled row can differ a little, as Tinker is not fully deterministic at temperature 0. Reading the first 40 answers twice changed 0 to 3 reasoned verdicts per juror.
