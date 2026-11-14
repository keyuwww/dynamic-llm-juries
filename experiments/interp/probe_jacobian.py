#!/usr/bin/env python3
"""
Overnight deep-dive, experiments 2 (Jacobian lens) + 4 (linear probes), combined into one capture
pass so we only pay the model-load cost once per model.

Why combined: both need the actual hidden-state vector at the forced-choice decision position, at
every layer, for a sample of items. The existing logit_lens_pilot.py only keeps the *logit-lens
readout* (p_correct_norm) per layer, not the hidden vectors themselves -- those are discarded after
each forward pass. This script re-runs the same forced-choice BFF setup but additionally:

  (2) Jacobian lens: for each layer l, backprop the scalar margin = logit_correct - logit_incorrect
      (read off the FINAL layer's output) back to the hidden state at layer l, and record
      ||d(margin)/d(h_l)||_2. This is the standard "local sensitivity" / saliency reading of a
      Jacobian lens (c.f. the gradient-based attribution literature; Sundararajan et al. 2017 for
      the general idea of a gradient norm as a per-position importance signal) -- it answers "how
      much does what layer l represents end up mattering to the model's final verdict," which is a
      different question from logit lens's "what does layer l *already* believe." A flat Jacobian
      norm across layers would mean no single layer is privileged; a sharp single peak would mean
      one layer's representation dominates the final decision.

  (4) Linear probes: save h_l itself (last-token hidden state, each layer) so a logistic-regression
      probe on gold correctness can be trained layer-by-layer, offline, after pulling results back
      (see train_probes.py). Only a modest per-item vector (hidden_size floats x n_layers) is kept,
      not full sequences/attention -- keeps the result file small even for 120B-class models.

Model: standard BFF forced-choice setup, same as logit_lens_pilot.py (same two rubrics available).
Sample size is deliberately modest (default 40 items) -- this is meant to establish *shape*
(does the Jacobian norm / probe accuracy curve look flat, single-peaked, multi-peaked across
layers) not to match the full 459-item significance-test sample size.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

from logit_lens_pilot import STANDARD_INSTR, RUBRICS, FORCED_CHOICE_SUFFIX, build_prompt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--rubric", choices=list(RUBRICS), default="rules")
    ap.add_argument("--out", default=None)
    ap.add_argument("--verdicts-path"), ap.add_argument("--bff-path")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from data import load_bff, load_verdicts_items, bff_key_to_uid  # noqa: E402

    items, dropped = load_verdicts_items(a.verdicts_path, a.bff_path, "unanimous")
    to_uid = bff_key_to_uid(load_bff(a.bff_path))
    for it in items:
        it["uid"] = to_uid.get(it["qid"], it["qid"])
        it["gold"] = it["human"]
    items = items[: a.limit]
    print(f"{len(items)} BFF items for probe/jacobian capture", flush=True)

    print(f"Loading {a.model} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()
    n_layers = model.config.num_hidden_layers
    print(f"Loaded. {n_layers} layers, device={model.device}", flush=True)

    tok_correct = tok.encode(" CORRECT", add_special_tokens=False)[0]
    tok_incorrect = tok.encode(" INCORRECT", add_special_tokens=False)[0]

    def capture(prompt):
        """One forward+backward pass. Returns per-layer hidden vec (detached, cpu, fp32) and
        per-layer jacobian norm d(margin)/d(h_l)."""
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        out = model(**inputs, output_hidden_states=True)
        hs = out.hidden_states  # embeddings + one per block, each needs grad already (no no_grad used)
        last = -1
        final_logits = out.logits[0, last, :]
        margin = final_logits[tok_correct] - final_logits[tok_incorrect]

        hvecs = [h[0, last, :].detach().float().cpu().tolist() for h in hs]
        # Single backward pass over ALL layers at once (not one retain_graph=True call per layer --
        # that retains the full saved-activation graph across every call and OOMs even a 4B model
        # on a 24GB GPU once you're ~10 layers in). torch.autograd.grad accepts a list of tensors
        # and returns one gradient per tensor from one traversal of the graph.
        grads = torch.autograd.grad(margin, list(hs), retain_graph=False, allow_unused=True)
        jac_norms = [float(g[0, last, :].norm().item()) if g is not None else None for g in grads]
        pred = "CORRECT" if final_logits[tok_correct] > final_logits[tok_incorrect] else "INCORRECT"
        del out, hs, grads
        return hvecs, jac_norms, pred

    out = Path(a.out or HERE / "overnight_deepdive" / "probe_data")
    out.mkdir(parents=True, exist_ok=True)
    tag = a.model.split("/")[-1].lower()
    cache_path = out / f"{tag}_{a.rubric}.jsonl"
    done = set()
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            done.add(json.loads(line)["id"])
        print(f"{len(done)} items already cached, resuming", flush=True)

    with open(cache_path, "a") as fh:
        for i, it in enumerate(items):
            if it["id"] in done:
                continue
            p_std = build_prompt(it, STANDARD_INSTR)
            hvecs, jacs, pred = capture(p_std)
            row = dict(id=it["id"], gold=it["gold"], pred_standard=pred,
                       hidden=hvecs, jacobian_norm=jacs)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            torch.cuda.empty_cache()  # scaling to 150-300 items OOM'd ~70 items in on a single
            # H100 without this -- fragmentation accumulates across items even though each
            # individual forward+backward is freed (del out, hs, grads in capture() above only
            # drops python refs, it doesn't return freed blocks to the OS/allocator pool).
            if (i + 1) % 5 == 0:
                print(f"  {i+1}/{len(items)}", flush=True)
    print(f"Done. Wrote {cache_path}", flush=True)


if __name__ == "__main__":
    main()
