# Exp 1: Jev as a correctness judge on BFF-Bench (baseline B7)

This asks TypeSafe Jev whether each model response in BFF-Bench is correct, and compares its answers with the consensus human labels from `kensho/VERDICTS`. Each response gets one yes/no question, asked in two conditions:

- **noref**: Jev sees only the conversation. This matches the no-reference setting in No Free Labels.
- **ref**: Jev also sees the expert reference answer from `kensho/BFFBench`.

## Run

From the repo root:

```bash
uv sync
export TYPESAFE_API_KEY=...                                   # from console.typesafe.ai
uv run python experiments/jev_bff/run_jev_bff.py --limit 40 --out experiments/jev_bff/jev_bff_results   # pilot
uv run python experiments/jev_bff/run_jev_bff.py --out experiments/jev_bff/jev_bff_results              # full run
```

Add `--mock` to check the whole pipeline with a fake judge, without a key. Reruns resume from the cache.

## Outputs

These go to the folder given by `--out`:

- `summary.md`:
  - κ, accuracy and AUROC against the human labels;
  - false-positive and false-negative rates;
  - results broken down by examinee model and by turn;
  - a selective-judging curve (accuracy and κ when Jev keeps only its most confident verdicts, i.e. the Path C tier-0 question);
  - cost and latency.
- `items.csv`: one row per item and condition.
- `predictions.jsonl`: the raw cache (git-ignored).

## Options

- `--consensus majority`: the default is unanimous agreement, dropping any "Not sure" labels.
- `--model jev-1.13.0`: pin the Jev version so results are reproducible.
- `--conditions noref`: run a single condition.
- `--workers 8`: parallel requests. The vendor limit is about 1,200 requests per minute.

## Reference point

No Free Labels reports GPT-4o at overall κ ≈ 0.69 with a human reference and ≈ 0.46 without one.
