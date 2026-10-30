#!/usr/bin/env python3
"""
Causal localization of the best-layer-to-final gap, on items where an interior layer's logit-lens
verdict already agrees with the human gold label but the model's own final answer doesn't.

Design rationale (see mech_interp_findings.html for the behavioral result this follows up on):
literature on this exact question warns that attribution -- reading off WHERE the logit-lens signal
visibly changes and calling that "the cause" -- is a weak localizer. "Opening LLM Judges" (Recovering
Preference Signals Beyond the Final Verdict, arXiv:2609.32407) finds direct attribution correlates
only rho=0.31 with true causal effect from patching/knockout (~82% of the effect is indirect/mediated),
and that causal decision depth is typically EARLIER than where the logit lens appears to "decide."
Halawi et al. 2024 ("Overthinking the Truth", arXiv:2307.09476) found the analogous late-layer
degradation (there: false few-shot demonstrations) is driven by a small number of attention heads
that ACTIVELY reintroduce the wrong answer, not generic forgetting -- a small, localized, ablatable
cause, not a diffuse one.

Neither paper's setup matches ours exactly (they both use two-condition contrasts: a biased vs.
debiased judge prompt, or true vs. false few-shot demonstrations). Our setup is single-prompt: the
SAME forward pass already contains the right answer at an earlier layer. That lets us run a same-pass
causal test neither paper needed: splice the model's own earlier hidden state forward in time, within
one forward call, instead of needing a second "clean" run to patch from.

Three stages:
  --stage selfpatch : for each flip item, capture the hidden state at the model's fixed best layer L
                       (via a forward hook), then re-run and overwrite a LATER layer K's output with
                       that captured value (last token only), for each candidate K in (L, flip_layer].
                       This IS causal (it changes what layer K+1 onward actually computes with), unlike
                       reading off where the logit-lens readout happens to flip. Reports the earliest K
                       where this recovers the gold verdict (the item's true "causal rescue depth").
  --stage ablate     : at the causal layer(s) --stage selfpatch identified, zero-ablate the WHOLE
                       attention-sublayer output and the WHOLE MLP-sublayer output (last token only)
                       WITHOUT any patched-in value, to test whether that layer's own fresh computation
                       is actively harmful (ablating it alone recovers the verdict -- a "false induction
                       head"-style active override) vs. merely failing to preserve the earlier signal
                       (self-patch recovers but plain ablation doesn't).
  --stage heads      : same idea as --stage ablate but one attention head at a time (zeroing its slice
                       of the o_proj input), restricted to --layers, to find which SPECIFIC head(s) are
                       responsible when --stage ablate flags attention as the active culprit.

Run on Qwen/Qwen3.5-9B as a negative control: its best layer IS effectively its final layer (not the
case where there's room for a gap), so it has very few flip items and these interventions should mostly
find nothing -- if they instead "recover" things just as often as for gpt-oss-120b, that's a sign the
method is finding ablation noise, not a real localized mechanism.

Usage (inside the Modal image):
  python experiments/interp/layer_gap_ablation.py --model openai/gpt-oss-120b --stage selfpatch --max-items 104
  python experiments/interp/layer_gap_ablation.py --model openai/gpt-oss-120b --stage ablate --max-items 104
  python experiments/interp/layer_gap_ablation.py --model openai/gpt-oss-120b --stage heads --layers 32 33 --max-items 40
  python experiments/interp/layer_gap_ablation.py --model Qwen/Qwen3.5-9B --stage selfpatch --max-items 13
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

from logit_lens_pilot import RUBRICS, build_prompt  # noqa: E402


def out_name(model, rubric):
    n = model.split("/")[-1].lower()
    return n if rubric == "rules" else f"{n}_{rubric}"


def kappa(y1, y2):
    n = len(y1)
    po = sum(1 for a, b in zip(y1, y2) if a == b) / n
    p1, p2 = sum(y1) / n, sum(y2) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return 1.0 if pe >= 0.999999 else (po - pe) / (1 - pe)


def best_layer(items):
    n_layers = len(items[0]["pcn_rules"])
    gold = [it["gold"] for it in items]
    best = None
    for L in range(n_layers):
        preds = [1 if it["pcn_rules"][L] >= 0.5 else 0 for it in items]
        k = kappa(gold, preds)
        if best is None or k > best[1]:
            best = (L, k)
    return best[0], n_layers


def flip_items(items, L):
    out = []
    for it in items:
        gold_label = "CORRECT" if it["gold"] else "INCORRECT"
        best_pred = "CORRECT" if it["pcn_rules"][L] >= 0.5 else "INCORRECT"
        if best_pred == gold_label and it["pred_rules"] != gold_label:
            out.append(it)
    return out


def flip_layer_of(it, L):
    """Earliest layer after L where the logit-lens verdict departs from gold and never returns --
    used only to bound the search window for --stage selfpatch, NOT as the causal answer itself."""
    n_layers = len(it["pcn_rules"])
    gold_label = "CORRECT" if it["gold"] else "INCORRECT"
    verdicts = ["CORRECT" if p >= 0.5 else "INCORRECT" for p in it["pcn_rules"]]
    last_wrong_run_start = None
    for l in range(L + 1, n_layers):
        if verdicts[l] != gold_label:
            if last_wrong_run_start is None:
                last_wrong_run_start = l
        else:
            last_wrong_run_start = None
    return last_wrong_run_start if last_wrong_run_start is not None else n_layers - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-oss-120b")
    ap.add_argument("--rubric", default="rules")
    ap.add_argument("--stage", choices=["selfpatch", "ablate", "heads"], default="selfpatch")
    ap.add_argument("--layers", type=int, nargs="*", default=None,
                     help="restrict to these layer indices (required for --stage heads; "
                          "for --stage ablate, defaults to each item's own selfpatch result)")
    ap.add_argument("--selfpatch-path", default=None,
                     help="path to a --stage selfpatch results json (required for --stage ablate/heads "
                          "unless --layers is given for every item some other way)")
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--control", action="store_true",
                     help="fragility control: instead of flip items (best-layer right, final wrong), "
                          "use items the model ALREADY gets right at the final layer, and check "
                          "whether single-head ablation BREAKS the correct answer. If a similarly "
                          "large fraction of heads break correct answers too, the heads-stage result "
                          "on flip items reflects generic decision-boundary fragility, not a specific "
                          "mechanism.")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from data import load_bff, load_verdicts_items, bff_key_to_uid  # noqa: E402

    results_dirname = out_name(a.model, a.rubric)
    pilot_path = HERE / "logit_lens_results" / results_dirname / "pilot_results.json"
    pilot = json.loads(pilot_path.read_text())
    items_pilot = pilot["items"]

    L, n_layers_logit = best_layer(items_pilot)
    if a.control:
        flips = [it for it in items_pilot
                 if it["pred_rules"] == ("CORRECT" if it["gold"] else "INCORRECT")]
        for it in flips:
            it["flip_layer"] = min(L + 5, n_layers_logit - 1)  # fixed window, no attribution to lean on
        if a.max_items:
            flips = flips[: a.max_items]
        print(f"model={a.model} rubric={a.rubric} [CONTROL]: {len(flips)} already-correct items "
              f"(testing whether ablation BREAKS a correct answer, not whether it recovers one)",
              flush=True)
    else:
        flips = flip_items(items_pilot, L)
        for it in flips:
            it["flip_layer"] = flip_layer_of(it, L)
        if a.max_items:
            flips = flips[: a.max_items]
        print(f"model={a.model} rubric={a.rubric}: fixed best layer={L}/{n_layers_logit - 1}, "
              f"{len(flips)} flip items (best-layer correct, final wrong), "
              f"attribution-based flip layers (upper bound for search, NOT the causal answer): "
              f"{[it['flip_layer'] for it in flips]}", flush=True)
    if not flips:
        print("No items -- nothing to test.", flush=True)
        return

    selfpatch_by_id = {}
    if a.stage in ("ablate", "heads") and a.selfpatch_path:
        sp = json.loads(Path(a.selfpatch_path).read_text())
        selfpatch_by_id = {r["id"]: r["causal_layer"] for r in sp["results"] if r.get("causal_layer") is not None}
        print(f"Loaded {len(selfpatch_by_id)} causal layers from {a.selfpatch_path}", flush=True)

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

    def d(pcn_idx):
        """pcn_rules/hidden_states index -> model.model.layers index. hidden_states[0] is the
        embedding layer (no decoder layer behind it); hidden_states[i] for i>=1 is the output of
        layers[i-1]. So decoder-layer index = pcn index - 1, valid for pcn index in [1, n_layers]."""
        return pcn_idx - 1

    def get_attn_meta(layer_idx):
        attn = layers[layer_idx].self_attn
        num_heads = (getattr(attn, "num_heads", None) or getattr(attn, "num_attention_heads", None)
                     or model.config.num_attention_heads)
        head_dim = getattr(attn, "head_dim", None) or (model.config.hidden_size // num_heads)
        o_proj = getattr(attn, "o_proj", None) or getattr(attn, "out_proj", None) or getattr(attn, "dense", None)
        return o_proj, num_heads, head_dim

    def run(prompt, hooks_fn=None):
        handles = hooks_fn() if hooks_fn else []
        try:
            inputs = tok(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model(**inputs)
            logits = out.logits[0, -1, :]
            pred = "CORRECT" if logits[tok_correct] > logits[tok_incorrect] else "INCORRECT"
        finally:
            for h in handles:
                h.remove()
        return pred

    # ---------- stage: selfpatch ----------
    # capture_idx/apply_idx are pcn_rules indices (so they line up with best_layer/flip_layer as
    # already reported); converted to decoder-layer indices via d() right at the hook boundary.
    def hooks_selfpatch(capture_idx, apply_idx, box):
        def cap_hook(mod, inp, out):
            h = out[0] if isinstance(out, tuple) else out
            box["val"] = h[0, -1, :].detach().clone()

        def apply_hook(mod, inp, out):
            h = out[0] if isinstance(out, tuple) else out
            h = h.clone()
            h[0, -1, :] = box["val"]
            return (h,) + out[1:] if isinstance(out, tuple) else h

        return [layers[d(capture_idx)].register_forward_hook(cap_hook),
                layers[d(apply_idx)].register_forward_hook(apply_hook)]

    # ---------- stage: ablate (whole sublayer, no patched-in value) ----------
    def hooks_ablate_block(layer_idx, kind):
        """layer_idx is a pcn_rules index, converted to decoder-layer index via d()."""
        module = layers[d(layer_idx)].self_attn if kind == "attn" else layers[d(layer_idx)].mlp

        def hook(mod, inp, out):
            h = out[0] if isinstance(out, tuple) else out
            h = h.clone()
            h[0, -1, :] = 0
            return (h,) + out[1:] if isinstance(out, tuple) else h

        return [module.register_forward_hook(hook)]

    # ---------- stage: heads ----------
    def hooks_ablate_head(layer_idx, head_idx):
        """layer_idx is a pcn_rules index, converted to decoder-layer index via d()."""
        o_proj, _, head_dim = get_attn_meta(d(layer_idx))

        def prehook(mod, args):
            x = args[0].clone()
            x[0, -1, head_idx * head_dim:(head_idx + 1) * head_dim] = 0
            return (x,) + args[1:]

        return [o_proj.register_forward_pre_hook(prehook)]

    results = []
    for r in flips:
        it = by_id[r["id"]]
        prompt = build_prompt(it, RUBRICS[a.rubric])
        gold_label = "CORRECT" if r["gold"] else "INCORRECT"

        pred_baseline = run(prompt)
        if pred_baseline != r["pred_rules"]:
            print(f"  [skip] {r['id']}: reproduction mismatch (got {pred_baseline}, expected {r['pred_rules']})",
                  flush=True)
            continue

        if a.stage == "selfpatch":
            window = list(range(L + 1, r["flip_layer"] + 1))
            causal_layer = None
            for K in window:
                box = {}
                pred = run(prompt, lambda K=K, box=box: hooks_selfpatch(L, K, box))
                if pred == gold_label:
                    causal_layer = K
                    break
            row = dict(id=r["id"], gold=gold_label, pred_baseline=pred_baseline, best_layer=L,
                       window=window, causal_layer=causal_layer)
            results.append(row)
            print(f"  {r['id']} (window {window}): self-patch from L{L} first recovers at "
                  f"K={causal_layer}", flush=True)

        elif a.stage == "ablate":
            K = selfpatch_by_id.get(r["id"])
            if K is None:
                print(f"  [skip] {r['id']}: no causal layer from selfpatch results", flush=True)
                continue
            row = dict(id=r["id"], gold=gold_label, pred_baseline=pred_baseline, causal_layer=K, ablations={})
            for kind in ("attn", "mlp"):
                pred = run(prompt, lambda K=K, kind=kind: hooks_ablate_block(K, kind))
                row["ablations"][kind] = dict(pred=pred, recovered=pred == gold_label)
            results.append(row)
            rec = [k for k, v in row["ablations"].items() if v["recovered"]]
            print(f"  {r['id']} (causal layer K={K}): plain-ablation recovers via {rec or 'neither'} "
                  f"(active override if non-empty; passive forgetting if empty)", flush=True)

        else:  # heads
            if not a.layers:
                raise SystemExit("--stage heads requires --layers")
            target = (lambda pred: pred != gold_label) if a.control else (lambda pred: pred == gold_label)
            verb = "break" if a.control else "recover"
            row = dict(id=r["id"], gold=gold_label, pred_baseline=pred_baseline, heads={}, control=a.control)
            for l in a.layers:
                if d(l) not in range(n_layers):
                    continue
                _, num_heads, _ = get_attn_meta(d(l))
                hit_heads = []
                for h in range(num_heads):
                    pred = run(prompt, lambda l=l, h=h: hooks_ablate_head(l, h))
                    if target(pred):
                        hit_heads.append(h)
                row["heads"][f"L{l}"] = dict(num_heads=num_heads, recovered_heads=hit_heads)
                print(f"  {r['id']} L{l}: {len(hit_heads)}/{num_heads} heads {verb} the verdict "
                      f"({hit_heads})", flush=True)
            results.append(row)

    suffix = {"selfpatch": "selfpatch", "ablate": "ablate",
              "heads": f"heads_L{'-'.join(map(str, a.layers or []))}"}[a.stage]
    if a.control:
        suffix += "_control"
    out_path = HERE / f"layer_gap_{results_dirname}_{suffix}.json"
    out_path.write_text(json.dumps(dict(model=a.model, rubric=a.rubric, stage=a.stage, best_layer=L,
                                         layers=a.layers, results=results), indent=2))
    n = len(results)
    if a.stage == "selfpatch":
        n_rescued = sum(1 for r in results if r["causal_layer"] is not None)
        print(f"\n{n_rescued}/{n} items rescued somewhere in-window by self-patching L{L} forward.")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
