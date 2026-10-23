# Judge confidence and numeric error injection

Plan and literature: [docs/judge_confidence_and_error_injection_plan.md](../../docs/judge_confidence_and_error_injection_plan.md).

Question: when a judge misses a numeric error in a realistic finance answer, is the error absent from its hidden
states (perception failure) or present but not used (readout failure), and how does that depend on the error's
visibility, size, digit place and the reference answer?

## Scripts (run from the repo root)

| Script | Does | Writes |
|---|---|---|
| `inject.py` | DeepSeek-V3.1 proposes one edit per (answer, variant type); the script applies and checks it | `results/raw/generator_calls.jsonl`, `results/raw/variants.jsonl` |
| `judge.py` | Tinker judges (gpt-oss-120b, Qwen3.6-35B-A3B, DeepSeek-V3.1) grade ORIG + passing variants, without and with the expert reference, 5 samples each, with top-5 log-probs at the verdict token | `results/raw/judgments.jsonl`, `results/pilot_summary.{md,json}` |
| `probe_local.py` | Local open judge (Qwen3.5-4B, thinking off, verdict forced right away) — P(CORRECT) and hidden states at the edit, the answer's end and the verdict | `results/raw/activations/<model>/` |

```
python experiments/judge_confidence/inject.py --limit 30
python experiments/judge_confidence/judge.py --limit-items 30
python experiments/judge_confidence/probe_local.py --limit-items 30
python experiments/judge_confidence/probe_local.py --analyze
```

All three resume from their caches: rerunning skips anything already stored, so nothing is paid for twice.

## Raw outputs (kept for reuse; git-ignored, so on this laptop only)

| File | One row per | Fields |
|---|---|---|
| `results/raw/generator_calls.jsonl` | DeepSeek call | `cache_key` (item\|examinee\|variant), full `prompt`, `raw` output, tokens, cost |
| `results/raw/variants.jsonl` | (item, variant) | `item_id`, `examinee`, `vtype`, `original`, `new` (full answer texts), `proposal` (edits, target old/new, explanation), `checks`, `ok` |
| `results/raw/judgments.jsonl` | (judge, text, condition) | `judge`, `model`, `renderer`, `text_id`, `vtype`, `condition` (none/human), `gold` (1 = still correct), full `prompt`, `samples` (text, verdict, P(CORRECT), verdict token, its top-5 alternatives, mean token log-prob), `vote_share`, `p_correct_mean`, sampling settings, tokens, cost |
| `results/raw/activations/<model>/index.jsonl` | (text, condition) | positions and their tokens, P(CORRECT), top-10 next tokens, `.npy` file name |
| `results/raw/activations/<model>/*.npy` | (text, condition) | float16 array (positions, layers + 1, hidden size) |

Back up `results/raw/` before deleting the folder; it is not in git.

## Variant types

ORIG (unchanged), V1 (final result contradicts the working), V2-10 / V2-1 / V2-x10 (one intermediate number off by
~10% / ~1% / ×10, carried through consistently), V2-lead (only the leading digit of that number changed), C1
(harmless rounding, still correct), C2 (paraphrase, still correct). Details and checks are in `inject.py`.
