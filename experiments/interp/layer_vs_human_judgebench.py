#!/usr/bin/env python3
"""
Cross-benchmark generalization check for the "does an interior layer already agree with humans
more than the final answer?" finding (see mech_interp_findings.html SS5), which was found on
BFF-Bench. This script runs the same logit-lens probe on JudgeBench (ScalerLab/JudgeBench,
arXiv:2410.12784) -- a pairwise A/B comparison task, algorithmic gold labels, completely different
format and domain from BFF-Bench's binary CORRECT/INCORRECT grading.

Single condition only (no standard-vs-rubric comparison): we just want each layer's own P(A) vs.
the algorithmic gold label, to see whether the same "interior layer beats final output" pattern
shows up on a different benchmark and task format.

Usage (inside the Modal image): python experiments/interp/layer_vs_human_judgebench.py --model ... --limit 459
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))

JUDGEBENCH_PROMPT = """You are comparing two AI assistant responses to the same question. Decide which response is better.

[QUESTION]
{question}

[RESPONSE A]
{response_a}

[RESPONSE B]
{response_b}

Which response is better -- more correct, more complete, more rigorous? Judge substance, not style or length.

Answer with exactly one letter, either A or B. Do not explain. Do not say anything else.

Answer:"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from data import load_judgebench  # noqa: E402

    items = load_judgebench()
    items = items[: a.limit]
    print(f"{len(items)} JudgeBench items", flush=True)

    print(f"Loading {a.model} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="auto")
    model.eval()
    n_layers = model.config.num_hidden_layers
    print(f"Loaded. {n_layers} layers, device={model.device}", flush=True)

    tok_a = tok.encode(" A", add_special_tokens=False)[0]
    tok_b = tok.encode(" B", add_special_tokens=False)[0]
    print(f"tok(A)={tok_a} ({tok.decode([tok_a])!r})  tok(B)={tok_b} ({tok.decode([tok_b])!r})", flush=True)

    def layerwise_scores(prompt):
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model(**inputs, output_hidden_states=True)
        hs = out.hidden_states
        pcn = []
        for h in hs:
            h_last = h[0, -1, :]
            normed = model.model.norm(h_last) if hasattr(model.model, "norm") else h_last
            logits = model.lm_head(normed)
            probs = torch.softmax(logits.float(), dim=-1)
            pa, pb = probs[tok_a].item(), probs[tok_b].item()
            pcn.append(pa / (pa + pb + 1e-12))
        final_logits = out.logits[0, -1, :]
        final_pred_a = bool(final_logits[tok_a] > final_logits[tok_b])
        return pcn, final_pred_a

    out = Path(a.out or HERE / "logit_lens_results" / f"judgebench_{a.model.split('/')[-1].lower()}")
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / "items.jsonl"
    done = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            r = json.loads(line)
            done[r["id"]] = r
        print(f"{len(done)} items already cached, resuming", flush=True)

    with open(cache_path, "a") as fh:
        for i, it in enumerate(items):
            if it["id"] in done:
                continue
            prompt = JUDGEBENCH_PROMPT.format(question=it["question"], response_a=it["response_a"],
                                               response_b=it["response_b"])
            pcn, final_pred_a = layerwise_scores(prompt)
            row = dict(id=it["id"], gold=it["gold"], final_pred_a=final_pred_a, pcn=pcn)
            done[it["id"]] = row
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(items)}", flush=True)

    results = [done[it["id"]] for it in items if it["id"] in done]
    (out / "pilot_results.json").write_text(json.dumps(dict(model=a.model, n_layers=n_layers, items=results), indent=2))
    print(f"Results written to {out / 'pilot_results.json'}")


if __name__ == "__main__":
    main()
