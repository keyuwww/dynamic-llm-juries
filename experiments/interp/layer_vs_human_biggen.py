#!/usr/bin/env python3
"""
Fourth-benchmark rubric-vs-standard check: does an interior layer already agree with humans more
than the final answer, and does grading WITH the benchmark's own human-written, instance-specific
rubric relocate/widen that gap the way BFF-Bench's researcher-written rubric did (see
mech_interp_findings.html SS5, and the gpt-oss-120b standard-vs-rules comparison: gap 0.197 -> 0.308
kappa, best layer 28% -> 86% depth)?

prometheus-eval/BiGGen-Bench-Results (arXiv:2406.05761, NAACL 2025): general-purpose LM capability
benchmark (9 capabilities, 77 tasks), each instance with a HUMAN-curated 1-5 scoring rubric (not
researcher-invented) and a human-assigned 1-5 score for a given model's response under that rubric.
Binarized to pass/fail (score>=4 -> CORRECT) to match this project's forced-choice setup.

Two conditions per item, same structure as logit_lens_pilot.py's standard-vs-rules:
  standard: holistic judgment with no rubric shown at all.
  rubric:   the item's own human-written criteria + all five score-level descriptions shown, asking
            whether the response would score 4-5 (CORRECT) or 1-3 (INCORRECT) under it.

Usage (inside the Modal image): python experiments/interp/layer_vs_human_biggen.py --model ... --limit 459
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))

FORCED_CHOICE_SUFFIX = (
    "\n\nAnswer with exactly one word, either CORRECT or INCORRECT. Do not explain. "
    "Do not say anything else.\n\nAnswer:"
)

STANDARD_TEMPLATE = """You are grading an AI assistant's response.

[SYSTEM MESSAGE GIVEN TO THE ASSISTANT]
{system_prompt}

[INPUT GIVEN TO THE ASSISTANT]
{input}

[ASSISTANT'S RESPONSE]
{response}

Is this response good -- genuinely helpful, correct, and appropriate for what was asked? Answer
CORRECT if it is a strong response overall, INCORRECT if it has significant problems.{suffix}"""

RUBRIC_TEMPLATE = """You are grading an AI assistant's response using a specific scoring rubric.

[SYSTEM MESSAGE GIVEN TO THE ASSISTANT]
{system_prompt}

[INPUT GIVEN TO THE ASSISTANT]
{input}

[REFERENCE ANSWER]
{reference_answer}

[ASSISTANT'S RESPONSE]
{response}

[SCORING RUBRIC]
Criteria: {criteria}
{score_descriptions}

Using this rubric, would the response score 4 or 5 (CORRECT) or 1, 2, or 3 (INCORRECT)?{suffix}"""


def build_prompts(it):
    score_descriptions = "\n".join(
        f"Score {k.replace('score', '').replace('_description', '')}: {v}"
        for k, v in sorted(it["rubric_scores"].items())
    )
    standard = STANDARD_TEMPLATE.format(system_prompt=it["system_prompt"], input=it["input"],
                                         response=it["response"], suffix=FORCED_CHOICE_SUFFIX)
    rubric = RUBRIC_TEMPLATE.format(system_prompt=it["system_prompt"], input=it["input"],
                                     reference_answer=it["reference_answer"], response=it["response"],
                                     criteria=it["rubric_criteria"], score_descriptions=score_descriptions,
                                     suffix=FORCED_CHOICE_SUFFIX)
    return standard, rubric


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from data import load_biggen_bench  # noqa: E402

    items = load_biggen_bench(limit=a.limit)
    print(f"{len(items)} BiGGen-Bench-Results (human_eval) items", flush=True)

    print(f"Loading {a.model} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="auto")
    model.eval()
    n_layers = model.config.num_hidden_layers
    print(f"Loaded. {n_layers} layers, device={model.device}", flush=True)

    tok_correct = tok.encode(" CORRECT", add_special_tokens=False)[0]
    tok_incorrect = tok.encode(" INCORRECT", add_special_tokens=False)[0]

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
            pc, pi = probs[tok_correct].item(), probs[tok_incorrect].item()
            pcn.append(pc / (pc + pi + 1e-12))
        final_logits = out.logits[0, -1, :]
        final_pred = "CORRECT" if final_logits[tok_correct] > final_logits[tok_incorrect] else "INCORRECT"
        return pcn, final_pred

    out = Path(a.out or HERE / "logit_lens_results" / f"biggen_{a.model.split('/')[-1].lower()}")
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
            p_std, p_rubric = build_prompts(it)
            pcn_standard, pred_standard = layerwise_scores(p_std)
            pcn_rubric, pred_rubric = layerwise_scores(p_rubric)
            row = dict(id=it["id"], gold=it["gold"], human_score=it["human_score"],
                       capability=it["capability"], task=it["task"],
                       pred_standard=pred_standard, pred_rubric=pred_rubric,
                       pcn_standard=pcn_standard, pcn_rubric=pcn_rubric)
            done[it["id"]] = row
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(items)}", flush=True)

    results = [done[it["id"]] for it in items if it["id"] in done]
    (out / "pilot_results.json").write_text(
        json.dumps(dict(model=a.model, n_layers=n_layers, items=results), indent=2))

    n = len(results)
    agree_std = sum(1 for r in results if (r["pred_standard"] == "CORRECT") == bool(r["gold"]))
    agree_rubric = sum(1 for r in results if (r["pred_rubric"] == "CORRECT") == bool(r["gold"]))
    print("\n" + "=" * 60)
    print(f"n={n} items, model={a.model} ({n_layers} layers)")
    print(f"Forced-choice agreement with gold: standard={agree_std}/{n}  rubric={agree_rubric}/{n}")
    print(f"Results written to {out / 'pilot_results.json'}")


if __name__ == "__main__":
    main()
