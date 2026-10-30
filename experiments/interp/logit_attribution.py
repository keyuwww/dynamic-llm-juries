#!/usr/bin/env python3
"""
Direct logit attribution (DLA) of the best-layer-to-final gap: for each flip item (best layer
agrees with gold, final answer doesn't), decompose EVERY layer's own fresh computation -- its
attention-sublayer write and its MLP-sublayer write to the residual stream, read directly off
the module output before it's added back in -- into how much it pushes the forced-choice logit
toward CORRECT vs INCORRECT, in a single ordinary forward pass (no ablation, no patching).

This generalizes --stage ablate (layer_gap_ablation.py) from a binary "does deleting this sublayer
recover the verdict" test into a continuous, per-layer, per-item signal of HOW MUCH and in WHICH
DIRECTION each sublayer pushes -- cheap (one forward pass per item, hooks only read) so it can be
run on every flip item and then sliced by subject/category/examinee/model to see whether the
*mechanism* (not just the *frequency*) of the gap differs by subject.

Standard DLA approximation (as used throughout the direct-logit-attribution mech-interp literature):
RMSNorm's denominator is treated as a near-constant scalar (dominated by the full final residual's
norm, not much moved by any single sublayer's write), so a sublayer write w's contribution to the
logit difference is approximated as ((w * norm.weight) / rms(final_residual)) . (u_pos - u_neg),
where u_pos/u_neg are the unembedding rows for the forced-choice tokens. This is a linear
approximation of a nonlinear (norm) step and is only meant to rank/compare contributions, not to
exactly reconstruct the true logit value.

Usage (inside the Modal image):
  python experiments/interp/logit_attribution.py --model openai/gpt-oss-120b --benchmark biggen_rubric --max-items 70
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

from layer_gap_ablation import BENCH, best_layer, flip_items  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-oss-120b")
    ap.add_argument("--benchmark", choices=list(BENCH), default="bff")
    ap.add_argument("--rubric", default="rules")
    ap.add_argument("--max-items", type=int, default=None)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    bench = BENCH[a.benchmark]
    results_dirname = bench["dirname_fn"](a.model, a.rubric)
    pilot_path = HERE / "logit_lens_results" / results_dirname / "pilot_results.json"
    pilot = json.loads(pilot_path.read_text())
    items_pilot = pilot["items"]

    L, n_layers_logit = best_layer(items_pilot, bench["pcn_field"])
    flips = flip_items(items_pilot, L, bench)
    if a.max_items:
        flips = flips[: a.max_items]
    print(f"model={a.model} benchmark={a.benchmark}: best_layer={L}/{n_layers_logit - 1}, "
          f"{len(flips)} flip items", flush=True)
    if not flips:
        print("No items -- nothing to do.", flush=True)
        return

    by_id = bench["load_items"](a.rubric)

    print(f"Loading {a.model} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.bfloat16, device_map="auto")
    model.eval()
    layers = model.model.layers
    n_layers = len(layers)
    print(f"Loaded. {n_layers} decoder layers, device={model.device}", flush=True)

    tok_pos = tok.encode(bench["tok_pos"], add_special_tokens=False)[0]
    tok_neg = tok.encode(bench["tok_neg"], add_special_tokens=False)[0]

    def d(pcn_idx):
        return pcn_idx - 1

    # device_map="auto" can put the final norm, lm_head, and individual decoder layers on
    # different GPUs; move every small vector used in the projection onto one fixed device (CPU)
    # to avoid chasing devices around model.hf_device_map.
    gain = model.model.norm.weight.detach().float().cpu() if hasattr(model.model, "norm") else None
    W_U = model.lm_head.weight.detach().float().cpu()
    u = W_U[tok_pos] - W_U[tok_neg]  # direction in NORMED hidden space: + pushes toward tok_pos

    window_pcn = list(range(L + 1, n_layers_logit))  # pcn indices, same convention as layer_gap_ablation
    window_dec = [d(p) for p in window_pcn]

    results = []
    for n_done, it in enumerate(flips):
        item = by_id.get(it["id"])
        if item is None:
            continue
        prompt = bench["prompt_fn"](item, a.rubric)
        inputs = tok(prompt, return_tensors="pt").to(model.device)

        writes = {}

        def make_hook(dec_idx, kind):
            def hook(mod, inp, out):
                h = out[0] if isinstance(out, tuple) else out
                writes[(dec_idx, kind)] = h[0, -1, :].detach().float()
            return hook

        handles = []
        for dec_idx in window_dec:
            handles.append(layers[dec_idx].self_attn.register_forward_hook(make_hook(dec_idx, "attn")))
            handles.append(layers[dec_idx].mlp.register_forward_hook(make_hook(dec_idx, "mlp")))

        with torch.no_grad():
            out = model(**inputs, output_hidden_states=True)
        for h in handles:
            h.remove()

        h_final = out.hidden_states[-1][0, -1, :].detach().float().cpu()
        rms_final = (h_final.pow(2).mean().sqrt() + 1e-6)

        gold_label = bench["label_pos"] if it["gold"] else bench["label_neg"]
        sign = 1.0 if gold_label == bench["label_pos"] else -1.0  # +1 means "toward gold is toward tok_pos"

        attn_proj, mlp_proj = [], []
        for p, dec_idx in zip(window_pcn, window_dec):
            # device_map="auto" can split layers across GPUs; captured writes may live on a
            # different device than u/gain/rms_final (computed from the final layer / lm_head).
            w_attn = writes.get((dec_idx, "attn")).cpu()
            w_mlp = writes.get((dec_idx, "mlp")).cpu()
            if gain is not None:
                pa = ((w_attn * gain) / rms_final) @ u
                pm = ((w_mlp * gain) / rms_final) @ u
            else:
                pa = (w_attn / rms_final) @ u
                pm = (w_mlp / rms_final) @ u
            # flip sign so positive always means "pushes AWAY from gold" (i.e. toward the wrong verdict)
            attn_proj.append(-sign * pa.item())
            mlp_proj.append(-sign * pm.item())

        results.append(dict(id=it["id"], gold=gold_label, best_layer=L,
                             window=window_pcn, attn_proj=attn_proj, mlp_proj=mlp_proj,
                             total_attn_push=sum(attn_proj), total_mlp_push=sum(mlp_proj)))
        if (n_done + 1) % 10 == 0:
            print(f"  {n_done + 1}/{len(flips)}", flush=True)

    out_path = HERE / f"logit_attribution_{results_dirname}_{a.benchmark}.json"
    out_path.write_text(json.dumps(dict(model=a.model, benchmark=a.benchmark, best_layer=L,
                                         window=window_pcn, results=results), indent=2))
    print(f"Results written to {out_path}")


if __name__ == "__main__":
    main()
