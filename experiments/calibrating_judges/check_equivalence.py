#!/usr/bin/env python
"""Is the vLLM pipeline (vllm_generate.py + acts_from_gen.py) equivalent to the HF pipeline (generate_judge.py --save-acts)?
Both are greedy on the same prompts, so the texts should agree except where bf16 numerics make an argmax flip.
Reports: share of identical texts, verdict agreement, and for the items with identical texts the cosine similarity of the activations at each layer
(should be ~1; the two forward passes differ only in padding / kernels). For items whose texts differ, the activation similarity is reported separately."""
import argparse, json
import numpy as np, pandas as pd


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--hf", required=True, help="prefix of the HF run, e.g. dir/Qwen3.5-4B__bff__uncertainty__n1_t0.0")
    ap.add_argument("--vllm", required=True, help="prefix of the vLLM run"); a = ap.parse_args()
    gh = pd.read_json(a.hf + "_gen.jsonl", lines=True, dtype={"item_id": str}).set_index("item_id"); gv = pd.read_json(a.vllm + "_gen.jsonl", lines=True, dtype={"item_id": str}).set_index("item_id")
    ah = np.load(a.hf + "_acts.npy").astype(np.float32); av = np.load(a.vllm + "_acts.npy").astype(np.float32)
    ih = pd.read_csv(a.hf + "_items.csv", dtype={"item_id": str})["item_id"].tolist(); iv = pd.read_csv(a.vllm + "_items.csv", dtype={"item_id": str})["item_id"].tolist()
    layers = json.load(open(a.hf + "_layers.json")); assert layers == json.load(open(a.vllm + "_layers.json")), "different layer sets"
    common = [i for i in ih if i in set(iv)]; ph = {i: k for k, i in enumerate(ih)}; pv = {i: k for k, i in enumerate(iv)}
    same = np.array([gh.loc[i, "text"].strip() == gv.loc[i, "text"].strip() for i in common])
    vh = gh.loc[common, "verdict"].values; vv = gv.loc[common, "verdict"].values; agree = np.array([(x == y) or (pd.isna(x) and pd.isna(y)) for x, y in zip(vh, vv)])
    print(f"{len(common)} items in common")
    print(f"identical texts: {same.mean():.3f}   same verdict: {agree.mean():.3f}   accuracy HF {gh.loc[common, 'correct'].mean():.3f}  vLLM {gv.loc[common, 'correct'].mean():.3f}")
    print(f"mean tokens HF {gh.loc[common, 'n_tokens'].mean():.0f}  vLLM {gv.loc[common, 'n_tokens'].mean():.0f}")
    A = np.stack([ah[ph[i]] for i in common]); B = np.stack([av[pv[i]] for i in common])
    cos = (A * B).sum(-1) / (np.linalg.norm(A, axis=-1) * np.linalg.norm(B, axis=-1) + 1e-9)                       # items x layers
    for name, m in (("identical-text items", same), ("items whose text differs", ~same)):
        if m.sum():
            print(f"\ncosine similarity of activations, {name} (n={m.sum()}), by layer:")
            print(pd.Series(cos[m].mean(0), index=layers).round(4).to_string())
    print("\nfirst differing position for items with different texts (characters):")
    for i, s in zip(common, same):
        if not s:
            x, y = gh.loc[i, "text"], gv.loc[i, "text"]; k = next((j for j in range(min(len(x), len(y))) if x[j] != y[j]), min(len(x), len(y))); print(f"  {i}: differ at char {k} of {len(x)} / {len(y)}")


if __name__ == "__main__":
    main()
