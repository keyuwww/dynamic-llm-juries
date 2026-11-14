#!/usr/bin/env python3
"""
Overnight deep-dive, step 5: Patchscopes (Ghandeharioun et al. 2024, arXiv:2401.06102) on a small,
hand-picked set of items -- qualitative illustration only, not a stats run.

Method: take the hidden state at the model's own critical/winning layer for the ORIGINAL
forced-choice prompt, then patch it into the LAST-token position of a fresh, short prompt
("The correct answer is:") run through the SAME model, and let the model continue generating from
there. If the patched hidden state carries the answer in a human-legible way, the continuation
should name CORRECT/INCORRECT (or the substantive answer) even when the original prompt's own
verbalized final answer disagreed with it.

This sidesteps logit-lens's basis-mismatch concern entirely -- we aren't projecting the hidden
state through the unembedding at all; we are letting the model itself verbalize what it encodes,
in its own forward computation, from a fresh context.

Usage: see modal entrypoint. Items are selected ahead of time (ids passed on the command line,
tagged with which category they illustrate) rather than sampled here.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

from logit_lens_pilot import STANDARD_INSTR, RUBRICS, build_prompt  # noqa: E402

PATCH_PROMPT = "Question: is the assistant's response correct or incorrect?\nThe correct answer is:"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--rubric", choices=list(RUBRICS) + ["standard"], default="rules")
    ap.add_argument("--layer", type=int, required=True)
    ap.add_argument("--ids", nargs="+", required=True, help="item ids to run, with a label each as id:label")
    ap.add_argument("--max-new-tokens", type=int, default=12)
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
    by_id = {it["id"]: it for it in items}

    wanted = {}
    for spec in a.ids:
        iid, label = spec.split(":", 1)
        wanted[iid] = label

    print(f"Loading {a.model} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()
    print(f"Loaded. device={model.device}", flush=True)

    patch_inputs = tok(PATCH_PROMPT, return_tensors="pt").to(model.device)
    patch_len = patch_inputs["input_ids"].shape[1]

    results = []
    for iid, label in wanted.items():
        it = by_id.get(iid)
        if it is None:
            print(f"SKIP {iid}: not found", flush=True)
            continue
        prompt = build_prompt(it, STANDARD_INSTR if a.rubric == "standard" else RUBRICS[a.rubric])
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model(**inputs, output_hidden_states=True)
            h_src = out.hidden_states[a.layer][0, -1, :].clone()  # the critical-layer hidden vector

            patched = {"done": False}

            def hook(module, inp, output):
                # Only patch the FIRST call (the prefill forward over the full prompt) -- generate()
                # re-invokes this hook on every subsequent decode step too (with KV caching, each of
                # those calls sees a sequence of length 1, i.e. just the newly generated token), and
                # clamping that position to h_src on every step as well produces a degenerate repeated-
                # token loop (observed: output collapsed to repeated "\n" or repeated " INC" tokens).
                if patched["done"]:
                    return output
                patched["done"] = True
                if isinstance(output, tuple):
                    hs = output[0]
                else:
                    hs = output
                hs[0, -1, :] = h_src.to(hs.dtype)
                if isinstance(output, tuple):
                    return (hs,) + output[1:]
                return hs

            # layer index a.layer-1 in model.model.layers corresponds to hidden_states[a.layer]
            # (hidden_states[0] is the embedding output, not a transformer block).
            block_idx = a.layer - 1
            if block_idx < 0:
                print(f"SKIP {iid}: layer {a.layer} is the embedding output, nothing to patch into a block", flush=True)
                continue
            handle = model.model.layers[block_idx].register_forward_hook(hook)
            try:
                gen = model.generate(**patch_inputs, max_new_tokens=a.max_new_tokens, do_sample=False)
            finally:
                handle.remove()
            continuation = tok.decode(gen[0, patch_len:], skip_special_tokens=True)

        row = dict(id=iid, label=label, gold=it["gold"], layer=a.layer, continuation=continuation)
        results.append(row)
        print(f"[{label}] id={iid} gold={it['gold']} -> continuation: {continuation!r}", flush=True)

    out_path = Path(a.out or HERE / "overnight_deepdive" / f"patchscopes_{a.model.split('/')[-1].lower()}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
