#!/usr/bin/env python3
"""
Overnight deep-dive, step 3: does gpt-oss-120b's gradient flow break at layer 19/36 because of its
native MXFP4-quantized MoE kernels lacking a backward pass? Test by loading the SAME model with
Mxfp4Config(dequantize=True) (dequantizes to bf16 on load -- ~4x the memory, so this needs an
H100:4-class box, not the H100:2 the native-MXFP4 load uses) and re-running the same
torch.autograd.grad probe used in probe_jacobian.py, on just a handful of items.

If gradients flow past layer 19 under dequantization -> confirms the native MXFP4 kernels are the
cause, and Jacobian lens on this model should always use the dequantized load path.
If they STILL break -> something else is going on (not simply a missing MXFP4 backward kernel),
report plainly rather than assuming.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

from logit_lens_pilot import STANDARD_INSTR, build_prompt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--model", default="openai/gpt-oss-120b")
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

    print(f"Loading {a.model} with dequantize=True ...", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    load_kwargs = dict(torch_dtype=torch.bfloat16, device_map="auto")
    quant_mode = "none"
    try:
        from transformers import Mxfp4Config
        load_kwargs["quantization_config"] = Mxfp4Config(dequantize=True)
        quant_mode = "Mxfp4Config(dequantize=True)"
    except Exception as e:
        print(f"Mxfp4Config not available in this transformers version ({e}); "
              f"loading plain bf16 and hoping from_pretrained auto-dequantizes.", flush=True)
    try:
        model = AutoModelForCausalLM.from_pretrained(a.model, **load_kwargs)
    except Exception as e:
        print(f"FAILED to load with {quant_mode}: {type(e).__name__}: {e}", flush=True)
        print(json.dumps({"quant_mode": quant_mode, "load_failed": True, "error": str(e)}), flush=True)
        return
    model.eval()
    n_layers = model.config.num_hidden_layers
    print(f"Loaded ({quant_mode}). {n_layers} layers, device={model.device}, "
          f"mem_allocated={torch.cuda.memory_allocated()/1e9:.1f}GB", flush=True)

    tok_correct = tok.encode(" CORRECT", add_special_tokens=False)[0]
    tok_incorrect = tok.encode(" INCORRECT", add_special_tokens=False)[0]

    results = []
    for it in items:
        prompt = build_prompt(it, STANDARD_INSTR)
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        out = model(**inputs, output_hidden_states=True)
        hs = out.hidden_states
        final_logits = out.logits[0, -1, :]
        margin = final_logits[tok_correct] - final_logits[tok_incorrect]
        grads = torch.autograd.grad(margin, list(hs), retain_graph=False, allow_unused=True)
        none_layers = [i for i, g in enumerate(grads) if g is None]
        norms = [None if g is None else float(g[0, -1, :].norm().item()) for g in grads]
        print(f"item {it['id']}: none_layers={none_layers}  norms[:25]={norms[:25]}", flush=True)
        results.append({"id": it["id"], "none_layers": none_layers, "jacobian_norm": norms})
        del out, hs, grads

    out_path = Path(a.out or HERE / "overnight_deepdive" / "mxfp4_backward_check.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "model": a.model, "quant_mode": quant_mode, "n_layers": n_layers, "items": results,
    }, indent=2))
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
