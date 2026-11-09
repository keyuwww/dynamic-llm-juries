#!/usr/bin/env python
"""The judge's own residual-stream activations at the LAST token of its generated output (the input of the probe in arXiv 2512.22245),
computed with one forward pass over prompt + the exact sampled tokens saved by vllm_generate.py (n-samples 1 file, with token_ids).

The last token is the end-of-turn token when the judge finished, else its last token when it was cut at max-new-tokens (same rule as generate_judge.py).
Activations are kept at every --layer-step-th layer (plus the last). Outputs: <tag>_acts.npy (items x layers x d, float16), _layers.json, _items.csv."""
import argparse, json, os, time
import numpy as np, pandas as pd, torch
from judge_data import load_items
from prompts import build_prompt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--bench", required=True, choices=["bff", "rb2safety", "judgebench", "ppe_correct", "ppe_pref"]); ap.add_argument("--gen", required=True, help="<tag>_gen.jsonl from vllm_generate.py (n-samples 1)")
    ap.add_argument("--data"); ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--jb-dir"); ap.add_argument("--prompt", default="uncertainty", choices=["uncertainty", "confidence"])
    ap.add_argument("--layer-step", type=int, default=2); ap.add_argument("--max-len", type=int, default=8192); ap.add_argument("--max-batch-tokens", type=int, default=60000)
    ap.add_argument("--out", required=True); ap.add_argument("--dtype", default="bfloat16"); ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    gen = pd.read_json(a.gen, lines=True); assert "token_ids" in gen and (gen["sample"] == 0).all(), "need an n-samples 1 file written by vllm_generate.py"
    items = {it["item_id"]: it for it in load_items(a.bench, a.data, a.verdicts_path, a.rb2_path, a.jb_dir)}
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    eos = tok.eos_token_id; eos_ids = set([eos] if isinstance(eos, int) else (eos or [])) | ({tok.convert_tokens_to_ids("<|im_end|>")} if "<|im_end|>" in tok.get_vocab() else set())
    end_id = tok.convert_tokens_to_ids("<|im_end|>") if "<|im_end|>" in tok.get_vocab() else eos

    def templ(text):
        msgs = [dict(role="user", content=text)]
        if getattr(tok, "chat_template", None) is None:
            return text
        try:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    seqs, ids_order, n_added = [], [], 0
    for r in gen.itertuples():
        p = tok(templ(build_prompt(a.bench, a.prompt, items[r.item_id])), add_special_tokens=False)["input_ids"][-a.max_len:]; g = list(r.token_ids)
        if r.finish_reason == "stop" and (not g or g[-1] not in eos_ids):                 # make the end-of-turn token part of the sequence, like HF generate does
            g.append(end_id); n_added += 1
        seqs.append(p + g); ids_order.append(r.item_id)
    print(f"{len(seqs)} sequences; length mean {np.mean([len(s) for s in seqs]):.0f} max {max(map(len, seqs))}; end token appended to {n_added}", flush=True)
    dt = getattr(torch, a.dtype)
    try:
        model = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, dtype=dt)
    except (TypeError, ValueError):
        model = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, torch_dtype=dt)
    model = model.to(a.device).eval()
    order = np.argsort([len(s) for s in seqs])[::-1]; batches, cur = [], []
    for i in order:
        if cur and (len(cur) + 1) * len(seqs[cur[0]]) > a.max_batch_tokens:
            batches.append(cur); cur = []
        cur.append(int(i))
    batches.append(cur); pad = tok.pad_token_id if tok.pad_token_id is not None else 0
    acts, layers, t0 = None, None, time.time()
    for b, idx in enumerate(batches):
        L = max(len(seqs[i]) for i in idx); ids = torch.full((len(idx), L), pad, dtype=torch.long); mask = torch.zeros((len(idx), L), dtype=torch.long)
        for r, i in enumerate(idx):                                                            # right padding: the pad tokens come after the real ones, so they cannot change them
            ids[r, :len(seqs[i])] = torch.tensor(seqs[i]); mask[r, :len(seqs[i])] = 1
        with torch.no_grad():
            try:                                                                          # we only need the hidden states, not the vocabulary logits (30 GB at 60k tokens)
                out = model(input_ids=ids.to(a.device), attention_mask=mask.to(a.device), output_hidden_states=True, use_cache=False, logits_to_keep=1)
            except TypeError:
                out = model(input_ids=ids.to(a.device), attention_mask=mask.to(a.device), output_hidden_states=True, use_cache=False)
        hs = out.hidden_states; Lm = len(hs) - 1
        if layers is None:
            layers = sorted(set(range(0, Lm + 1, a.layer_step)) | {Lm}); acts = np.zeros((len(seqs), len(layers), hs[0].shape[-1]), dtype=np.float16)
            print(f"{Lm} transformer layers; capturing hidden_states at {layers}", flush=True)
        for r, i in enumerate(idx):
            acts[i] = torch.stack([hs[l][r, len(seqs[i]) - 1, :] for l in layers]).float().cpu().numpy().astype(np.float16)
        del out, hs
        if b % 20 == 0 or b == len(batches) - 1:
            print(f"batch {b + 1}/{len(batches)}  {time.time() - t0:.0f}s", flush=True)
    assert np.isfinite(acts.astype(np.float32)).all(), "non-finite activations"
    os.makedirs(a.out, exist_ok=True); tag = os.path.basename(a.gen).replace("_gen.jsonl", "")
    np.save(os.path.join(a.out, f"{tag}_acts.npy"), acts); json.dump(layers, open(os.path.join(a.out, f"{tag}_layers.json"), "w"))
    pd.DataFrame({"item_id": ids_order, "group": [items[i]["group"] for i in ids_order]}).to_csv(os.path.join(a.out, f"{tag}_items.csv"), index=False)
    print(f"saved {tag}_acts.npy {acts.shape}", flush=True)


if __name__ == "__main__":
    main()
