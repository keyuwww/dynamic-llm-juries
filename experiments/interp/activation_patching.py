#!/usr/bin/env python3
"""
Causal activation patching, following Wang et al. 2025 (arXiv:2508.02087): does swapping the
hidden state at a layer (or a small window of layers) between two prompt conditions actually
CAUSE the verdict to change, or does it just correlate?

Generalized over two axes:
  --model: any model already run through logit_lens_pilot.py (reads its pilot_results.json).
  --flip: which direction of verdict flip to test causally --
      std_to_incorrect  = standard CORRECT -> rules INCORRECT (the "gets stricter" shift, e.g.
                           gpt-oss-20b)
      std_to_correct    = standard INCORRECT -> rules CORRECT (the "gets more lenient" shift,
                           e.g. qwen3.5-9b)
  --window: how many consecutive layers to patch jointly, centered on each item's own interior
            critical layer (1 = just that layer, matching the original single-layer test).

IMPORTANT: the "critical layer" is the peak KL divergence among INTERIOR layers only (excluding
the final layer, whose hidden state feeds straight into the lm_head readout and trivially
dominates any whole-network KL comparison -- see logit_lens_pilot.py's fix).

Design per item, at its own interior critical layer(s) L (a window of `--window` layers centered
on it, clipped to valid range):
  - Suppression: run the condition that produced the WORSE verdict (rules, for std_to_incorrect),
    patch in the hidden states from the condition that produced the BETTER verdict (standard),
    at every layer in the window, last token position only. Does the verdict flip back?
  - Induction: the reverse -- run the BETTER condition, patch in the WORSE condition's hidden
    states over the same window. Does the verdict flip to match the worse one?

Usage (inside the Modal image):
  python experiments/interp/activation_patching.py --model openai/gpt-oss-20b --flip std_to_incorrect --window 1
  python experiments/interp/activation_patching.py --model openai/gpt-oss-20b --flip std_to_incorrect --window 3
  python experiments/interp/activation_patching.py --model Qwen/Qwen3.5-9B --flip std_to_correct --window 1
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

from logit_lens_pilot import STANDARD_INSTR, build_prompt  # noqa: E402


def out_name(model):
    return model.split("/")[-1].lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-oss-20b")
    ap.add_argument("--rubric", default="rules")
    ap.add_argument("--flip", choices=["std_to_incorrect", "std_to_correct"], default="std_to_incorrect")
    ap.add_argument("--window", type=int, default=1, help="number of consecutive layers to patch jointly")
    ap.add_argument("--max-items", type=int, default=None)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from data import load_bff, load_verdicts_items, bff_key_to_uid  # noqa: E402
    from logit_lens_pilot import RUBRICS  # noqa: E402

    results_dirname = out_name(a.model) if a.rubric == "rules" else f"{out_name(a.model)}_{a.rubric}"
    pilot_path = HERE / "logit_lens_results" / results_dirname / "pilot_results.json"
    pilot = json.loads(pilot_path.read_text())

    if a.flip == "std_to_incorrect":
        better, worse = "CORRECT", "INCORRECT"
    else:
        better, worse = "INCORRECT", "CORRECT"
        # for std_to_correct, "standard" is the worse verdict and "rules" is the better one
    flips = [r for r in pilot["items"]
             if (r["pred_standard"] == ("CORRECT" if a.flip == "std_to_incorrect" else "INCORRECT"))
             and (r["pred_rules"] == ("INCORRECT" if a.flip == "std_to_incorrect" else "CORRECT"))]
    if a.max_items:
        flips = flips[: a.max_items]
    for r in flips:
        interior = r["kl_per_layer"][:-1]
        r["interior_critical_layer"] = max(range(len(interior)), key=lambda l: interior[l])
    print(f"model={a.model} flip={a.flip} window={a.window}: {len(flips)} flip items, "
          f"interior critical layers: {[r['interior_critical_layer'] for r in flips]}", flush=True)
    if not flips:
        print("No flip items of this type -- nothing to patch.", flush=True)
        return

    items, _ = load_verdicts_items(None, None, "unanimous")
    to_uid = bff_key_to_uid(load_bff(None))
    for it in items:
        it["uid"] = to_uid.get(it["qid"], it["qid"])
    by_id = {it["id"]: it for it in items}

    print(f"Loading {a.model} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="auto")
    model.eval()
    layers = model.model.layers
    n_layers = len(layers)
    print(f"Loaded. {n_layers} decoder layers, device={model.device}", flush=True)

    tok_correct = tok.encode(" CORRECT", add_special_tokens=False)[0]
    tok_incorrect = tok.encode(" INCORRECT", add_special_tokens=False)[0]

    def run(prompt, patch_layer_idxs=None, patch_values=None, capture_layer_idxs=None):
        """One forward pass. patch_layer_idxs/patch_values: parallel lists -- overwrite each named
        layer's output at the last token with the matching captured value. capture_layer_idxs:
        return a dict {layer_idx: captured value at last token} for later use as patch_values."""
        captured = {}
        handles = []
        if patch_layer_idxs:
            for idx, val in zip(patch_layer_idxs, patch_values):
                def make_patch_hook(v):
                    def patch_hook(module, inp, out):
                        h = out[0] if isinstance(out, tuple) else out
                        h = h.clone()
                        h[0, -1, :] = v
                        return (h,) + out[1:] if isinstance(out, tuple) else h
                    return patch_hook
                handles.append(layers[idx].register_forward_hook(make_patch_hook(val)))
        if capture_layer_idxs:
            for idx in capture_layer_idxs:
                def make_capture_hook(i):
                    def capture_hook(module, inp, out):
                        h = out[0] if isinstance(out, tuple) else out
                        captured[i] = h[0, -1, :].detach().clone()
                    return capture_hook
                handles.append(layers[idx].register_forward_hook(make_capture_hook(idx)))
        try:
            inputs = tok(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model(**inputs)
            logits = out.logits[0, -1, :]
            pred = "CORRECT" if logits[tok_correct] > logits[tok_incorrect] else "INCORRECT"
        finally:
            for h in handles:
                h.remove()
        return pred, captured

    results = []
    for r in flips:
        it = by_id[r["id"]]
        p_std = build_prompt(it, STANDARD_INSTR)
        p_rules = build_prompt(it, RUBRICS[a.rubric])
        L = r["interior_critical_layer"]
        half = a.window // 2
        window_layers = [l for l in range(L - half, L - half + a.window) if 0 <= l < n_layers - 1]

        pred_std, cap_std = run(p_std, capture_layer_idxs=window_layers)
        pred_rules, cap_rules = run(p_rules, capture_layer_idxs=window_layers)
        pred_better = pred_std if better == "CORRECT" else pred_rules  # the "better"-condition's own prediction
        pred_worse = pred_rules if better == "CORRECT" else pred_std

        if pred_std != r["pred_standard"] or pred_rules != r["pred_rules"]:
            print(f"  [skip] {r['id']}: reproduction mismatch (std={pred_std}, rules={pred_rules})", flush=True)
            continue

        values_better = cap_std if better == "CORRECT" else cap_rules
        values_worse = cap_rules if better == "CORRECT" else cap_std
        prompt_worse = p_rules if better == "CORRECT" else p_std
        prompt_better = p_std if better == "CORRECT" else p_rules

        pred_suppressed, _ = run(prompt_worse, patch_layer_idxs=window_layers,
                                  patch_values=[values_better[l] for l in window_layers])
        pred_induced, _ = run(prompt_better, patch_layer_idxs=window_layers,
                               patch_values=[values_worse[l] for l in window_layers])

        row = dict(id=r["id"], layers=window_layers, pred_standard=pred_std, pred_rules=pred_rules,
                   pred_worse_with_better_patch=pred_suppressed,
                   pred_better_with_worse_patch=pred_induced,
                   suppression_recovered=pred_suppressed == better,
                   induction_flipped=pred_induced == worse)
        results.append(row)
        print(f"  {r['id']} (layers {window_layers}): worse-run+better-patch -> {pred_suppressed}  "
              f"| better-run+worse-patch -> {pred_induced}", flush=True)

    out_path = HERE / f"activation_patching_{results_dirname}_{a.flip}_w{a.window}.json"
    out_path.write_text(json.dumps(dict(model=a.model, flip=a.flip, window=a.window, results=results), indent=2))

    n = len(results)
    if n == 0:
        print("No reproducible flip items -- nothing to report.", flush=True)
        return
    n_suppressed = sum(r["suppression_recovered"] for r in results)
    n_induced = sum(r["induction_flipped"] for r in results)
    print("\n" + "=" * 60)
    print(f"model={a.model}  flip={a.flip}  window={a.window}  n={n}")
    print(f"Suppression (patch BETTER activation into WORSE run): {n_suppressed}/{n} recovered")
    print(f"Induction (patch WORSE activation into BETTER run): {n_induced}/{n} flipped")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
