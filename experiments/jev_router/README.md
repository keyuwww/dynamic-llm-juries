# Exp 2: Jev / CLM as certifier and router on BFF-Bench

**Question:** before any model answers, can a System One model tell *which* models will get a question right? This is the "certify judges per question" step of Dynamic Juries (Path A).

For each BFF-Bench question-turn, the backend sees **only the question(s)**, never an answer. One request asks:

- one **yes/no** question per model: "Will ⟨model⟩ answer correctly?". The models are scored independently, which gives the jury view.
- one **choice** question: "Which model is most likely correct?", with the six models plus **none** as options. This is the direct routing view.

The ground truth is whether that model's real answer was marked Correct by the human graders in `kensho/VERDICTS`. No answers are generated, and the full run is about 160 requests.

## Run (from repo root)

```bash
uv run python experiments/jev_router/run_jev_router.py --mock                 # offline check
uv run python experiments/jev_router/run_jev_router.py --limit 30             # Jev pilot (needs TYPESAFE_API_KEY)
uv run python experiments/jev_router/run_jev_router.py                        # Jev full
uv run python experiments/jev_router/run_jev_router.py --backend clm          # CLM-8B (needs a CLM server, below)
uv run python experiments/compare_backends.py                                 # Jev vs CLM table → experiments/backend_comparison.md
```

Results go to `experiments/jev_router/<backend>_router_results/`, which holds `summary.md`, `metrics.json`, `certifier_items.csv` and a calibration PNG. The PNG needs matplotlib: run `uv add matplotlib`.

## What `summary.md` reports

1. **Certifier quality.** AUROC and Brier, compared with a *prior* baseline that uses each model's average accuracy on the other questions.
2. **Routing.** Accuracy of the chosen model, routed two ways: highest yes/no P, and the choice question's top pick. These are compared with a random model, the best single model and an oracle. For the choice question, it also reports how well P(none) spots questions where every model fails.
3. **Cost-aware routing.** Send each question to the smallest model the backend certifies at ≥ τ.
4. **Certification sets (the jury view).** At each τ it reports:
   - how many models get certified;
   - precision and recall;
   - how often *no* model is certified.
5. **Calibration.** Reliability table, ECE and Brier.

## Running CLM-8B on Modal (easiest)

```bash
uv add modal
uv run modal token set --token-id <id> --token-secret <secret>   # your Modal keys, once (never commit them)
uv run modal run experiments/clm_modal.py --limit 30             # pilot: router test on an L40S GPU
uv run modal run experiments/clm_modal.py                        # full router test
uv run modal run experiments/clm_modal.py --judge                # + judge test (Exp 1)
uv run python experiments/compare_backends.py                    # Jev vs CLM table
```

`clm_modal.py` builds a GPU container with vLLM and CLM, starts both servers, runs the experiments inside Modal, and writes the results into `experiments/*/clm_*_results/` on your laptop. The first run downloads Qwen3-8B (~16 GB) into a cached Modal Volume, which takes about 5 minutes. After that, a run takes a few minutes, roughly $2/hour of GPU time.

## Running CLM-8B on your own GPU

CLM is open (Apache 2.0) but self-hosted, and it needs an **NVIDIA GPU**: Qwen3-8B uses about 16 GB. Options are Modal (AC215 credits), a Harvard FASRC GPU node, or a Colab/cloud GPU.

```bash
# on the GPU machine
git clone https://github.com/Contrastive-LM/CLM.git && cd CLM && pip install -r requirements.txt && pip install -e .
vllm serve Qwen/Qwen3-8B --served-model-name qwen3-8b --runner pooling \
     --enable-prefix-caching --max-model-len 2048 --gpu-memory-utilization 0.35 --port 8090 &
clm-serve --port 8700 --emb-url http://127.0.0.1:8090/v1/embeddings
```

Then, from wherever you run the experiment (the GPU box, or your laptop through an SSH tunnel):

```bash
uv pip install contrastive-lm          # or: uv pip install -e /path/to/CLM
uv run python experiments/jev_router/run_jev_router.py --backend clm --clm-url http://127.0.0.1:8700
uv run python experiments/jev_bff/run_jev_bff.py --backend clm --clm-url http://127.0.0.1:8700   # judge test too
```

Note: CLM's `--max-model-len 2048` limits how long the text sent to it can be. BFF questions fit, but the judge test (Exp 1) sends whole conversations, so raise the limit if requests fail.

## Calibration of the judge run (Exp 1)

```bash
uv run python analysis/calibration.py experiments/jev_bff/jev_bff_results/items.csv --prob p --label human --group cond
```
