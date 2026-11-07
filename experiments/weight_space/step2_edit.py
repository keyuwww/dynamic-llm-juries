#!/usr/bin/env python3
"""
Step 2 on RB2 Safety: make Step 1's fix permanent in the weights (no hooks, no outside detector at run time).

2a  "Add a connection": in one MLP block b (after the layer-14 "knows" signal, before the verdict), pick N existing
    neurons whose activations at the verdict position linearly predict the knows score z (fit on TRAIN), and change
    only those neurons' output weights (columns of down_proj) so they also write  alpha * |h| * (k . a) * u  into the
    residual, where u is the model's own "says CORRECT" direction at that depth (from Step 1).
        delta W_down[:, N] = alpha * |h| * u k^T          (rank 1, N x 1024 weights)
    The edit is always on, at every token of every prompt. Tuned on DEV: block in {16, 19, 22}, N, alpha.
2b  "Delete a direction" test (Experiment 8 style): does any later component actively erase the signal? Zero the
    attention / MLP output of each block 14..23 at the verdict position and see whether the verdict AUROC rises.
final  the chosen 2a edit, scored once on TEST, plus side effects: BFF and JudgeBench test splits (vs the stored
    unedited verdicts), next-token loss on WikiText-2, and a few generations; the edit is saved as a diff.

  .venv/bin/python experiments/weight_space/step2_edit.py acts
  .venv/bin/python experiments/weight_space/step2_edit.py tune
  .venv/bin/python experiments/weight_space/step2_edit.py ablate
  .venv/bin/python experiments/weight_space/step2_edit.py final
"""
import argparse, json, sys, time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gap_check as gc  # noqa: E402
import smoke  # noqa: E402
import step1_nudge as s1  # noqa: E402

OUT = HERE / "results" / "raw" / "step2"
BLOCKS = {16: 17, 19: 20, 22: 23}  # MLP block -> hidden-state index it writes into (u and |h| from Step 1)
NS = (16, 64, 256)
ALPHAS = (0.02, 0.05, 0.1, 0.2)


def load():
    import torch
    recs = s1.load_items()
    z, _ = s1.fit_knows(recs)
    tok, model, dev = smoke.load_model()
    d = torch.load(s1.OUT / "directions.pt")
    u = {L: v.to(dev) for L, v in d["u"].items()}
    return recs, z, tok, model, dev, u, d["scale"], d["pos_id"], d["neg_id"]


def mlp(model, b):
    return model.model.language_model.layers[b].mlp


# ----------------------------------------------------------------------------- neuron activations at the verdict
def acts(a):
    import torch
    recs, z, tok, model, dev, u, scale, pos_id, neg_id = load()
    OUT.mkdir(parents=True, exist_ok=True)
    sel = [i for i, r in enumerate(recs) if r["split"] in ("train", "dev")]
    store = {b: [] for b in BLOCKS}
    cur = {}
    hooks = [mlp(model, b).down_proj.register_forward_pre_hook(
        lambda m, inp, b=b: cur.__setitem__(b, inp[0][0, -1].float().cpu().numpy())) for b in BLOCKS]
    t = time.time()
    try:
        for k, i in enumerate(sel):
            with torch.no_grad():
                model(**s1.encode(tok, recs[i]["text"], dev), logits_to_keep=1, use_cache=False)
            for b in BLOCKS:
                store[b].append(cur[b])
            if (k + 1) % 100 == 0:
                print(f"  acts {k + 1}/{len(sel)} {time.time() - t:.0f}s", flush=True)
    finally:
        for h in hooks:
            h.remove()
    np.savez(OUT / "acts.npz", idx=np.array(sel), **{f"b{b}": np.stack(v) for b, v in store.items()})
    print(f"activations for {len(sel)} train+dev items in {time.time() - t:.0f}s")


def fit_key(A, z, n, tr):
    """Pick the n neurons most correlated with z on train; least-squares weights k (no intercept) so k.a ~ z."""
    At, zt = A[tr], z[tr]
    c = np.abs([np.corrcoef(At[:, j], zt)[0, 1] if At[:, j].std() > 0 else 0 for j in range(A.shape[1])])
    idx = np.argsort(-np.nan_to_num(c))[:n]
    X = At[:, idx]
    lam = 1e-3 * np.trace(X.T @ X) / n
    k = np.linalg.solve(X.T @ X + lam * np.eye(n), X.T @ zt)
    return np.sort(idx), k[np.argsort(idx)]


class Edit:
    """Apply / revert delta W_down[:, idx] = alpha * s * u k^T in place (bf16), recording the realized change."""

    def __init__(self, model, b, idx, k, u, s, alpha):
        import torch
        self.W = mlp(model, b).down_proj.weight
        self.idx = torch.as_tensor(idx, device=self.W.device)
        self.orig = self.W[:, self.idx].clone()
        delta = (alpha * s) * u.float()[:, None] * torch.as_tensor(k, dtype=torch.float32, device=self.W.device)[None, :]
        self.intended = delta
        self.n_weights = int(delta.numel())

    def __enter__(self):
        import torch
        with torch.no_grad():
            self.W[:, self.idx] = (self.orig.float() + self.intended).to(self.W.dtype)
            real = self.W[:, self.idx].float() - self.orig.float()
        self.rel_err = float((real - self.intended).norm() / self.intended.norm())
        return self

    def __exit__(self, *exc):
        import torch
        with torch.no_grad():
            self.W[:, self.idx] = self.orig


def verdicts(tok, model, dev, texts, pos_id, neg_id, hook=None):
    import torch
    ps = []
    for t in texts:
        with torch.no_grad():
            lg = model(**s1.encode(tok, t, dev), logits_to_keep=1, use_cache=False).logits[0, -1].float()
        ps.append(float(torch.sigmoid(lg[pos_id] - lg[neg_id])))
    return np.array(ps)


# ----------------------------------------------------------------------------- 2a tuning on dev
def tune(a):
    recs, z, tok, model, dev, u, scale, pos_id, neg_id = load()
    S = np.load(OUT / "acts.npz")
    idx_all = S["idx"]
    tr = np.array([recs[i]["split"] == "train" for i in idx_all])
    zz = z[idx_all]
    D = [recs[i] for i in idx_all[~tr]]
    y = np.array([r["gold"] for r in D])
    strata = np.array([r["stratum"] for r in D])
    texts = [r["text"] for r in D]
    out = OUT / "tune_dev.jsonl"
    rows = [json.loads(l) for l in open(out)] if out.exists() else []
    done = {(r["block"], r["n"], r["alpha"]) for r in rows}

    def run(b, n, al, fh):
        if (b, n, al) in done:
            return next(r for r in rows if (r["block"], r["n"], r["alpha"]) == (b, n, al))
        A = S[f"b{b}"]
        idx, k = fit_key(A, zz, n, tr)
        fit_r = float(np.corrcoef(A[~tr][:, idx] @ k, zz[~tr])[0, 1])
        L = BLOCKS[b]
        with Edit(model, b, idx, k, u[L], scale[L], al) as e:
            p = verdicts(tok, model, dev, texts, pos_id, neg_id)
        row = dict(block=b, n=n, alpha=al, n_weights=e.n_weights, bf16_rel_err=e.rel_err, key_r_dev=fit_r,
                   **s1.metrics(y, p, strata))
        fh.write(json.dumps(row) + "\n"), fh.flush()
        rows.append(row)
        print(f"block {b} N={n:<4} a={al:<5} key r={fit_r:.2f} bf16 err {e.rel_err:.2f} | AUROC {row['auroc']:.3f} "
              f"same-source {row['auroc_same_source']:.3f} says-CORRECT {row['says_correct']:.0%} "
              f"bal-acc {row['bal_acc']:.3f}", flush=True)
        return row

    with open(out, "a") as fh:
        # stage 1: every block at N = 64
        for b in BLOCKS:
            for al in ALPHAS:
                run(b, 64, al, fh)
        best_b = max((r for r in rows if r["n"] == 64), key=lambda r: r["auroc_same_source"])["block"]
        # stage 2: neuron count at the best block
        for n in NS:
            for al in ALPHAS:
                run(best_b, n, al, fh)
    (OUT / "tune_dev_all.json").write_text(json.dumps(rows, indent=0))


# ----------------------------------------------------------------------------- 2b: does anything erase the signal?
def ablate(a):
    import torch
    recs, z, tok, model, dev, u, scale, pos_id, neg_id = load()
    D = [r for r in recs if r["split"] == "dev"]
    y = np.array([r["gold"] for r in D])
    strata = np.array([r["stratum"] for r in D])
    texts = [r["text"] for r in D]
    out = OUT / "ablate_dev.jsonl"
    rows = [json.loads(l) for l in open(out)] if out.exists() else []
    done = {(r["block"], r["part"]) for r in rows}
    layers = model.model.language_model.layers
    with open(out, "a") as fh:
        for b in range(14, 24):
            for part in ("attn", "mlp"):
                if (b, part) in done:
                    continue
                L = layers[b]
                mod = L.mlp if part == "mlp" else (L.self_attn if hasattr(L, "self_attn") else L.linear_attn)

                def hook(_m, _i, o):
                    if isinstance(o, tuple):
                        o[0][:, -1, :] = 0
                    else:
                        o[:, -1, :] = 0
                    return o
                h = mod.register_forward_hook(hook)
                try:
                    p = verdicts(tok, model, dev, texts, pos_id, neg_id)
                finally:
                    h.remove()
                row = dict(block=b, part=part, kind="full" if hasattr(L, "self_attn") else "linear",
                           **s1.metrics(y, p, strata))
                fh.write(json.dumps(row) + "\n"), fh.flush()
                rows.append(row)
                print(f"zero {part:4s} of block {b} ({row['kind']}): AUROC {row['auroc']:.3f} same-source "
                      f"{row['auroc_same_source']:.3f} says-CORRECT {row['says_correct']:.0%}", flush=True)
    (OUT / "ablate_dev_all.json").write_text(json.dumps(rows, indent=0))


# ----------------------------------------------------------------------------- final: test + side effects
def wikitext_loss(tok, model, dev, n_chunks=80, length=256):
    import torch
    from datasets import load_dataset
    text = "\n\n".join(t for t in load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1", split="test")["text"] if t.strip())
    ids = tok(text, return_tensors="pt")["input_ids"][0]
    losses = []
    for c in range(n_chunks):
        x = ids[c * length:(c + 1) * length][None].to(dev)
        with torch.no_grad():
            lg = model(input_ids=x, use_cache=False).logits[0, :-1].float()
        losses.append(float(torch.nn.functional.cross_entropy(lg, x[0, 1:])))
    return float(np.mean(losses))


def generations(tok, model, dev):
    import torch
    prompts = ["Explain in two sentences why the sky is blue.",
               "Write a short, friendly reply declining a meeting invitation.",
               "What is 17 times 23? Show the steps."]
    outs = []
    for p in prompts:
        enc = tok(tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True,
                                          enable_thinking=False), return_tensors="pt").to(dev)
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=60, do_sample=False)
        outs.append(dict(prompt=p, text=tok.decode(g[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)))
    return outs


def other_bench(tok, model, dev, bench):
    """Test split of another benchmark: verdicts with the edit vs the stored unedited ones."""
    recs = [json.loads(l) for l in open(gc.RAW / bench / "index.jsonl")]
    items = {it["id"]: it for it in gc.LOADERS[bench]()}
    R = [r for r in recs if r["split"] == "test"]
    pos, neg = smoke.TOKENS[bench]
    pid, nid = (tok.encode(w, add_special_tokens=False)[0] for w in (pos, neg))
    p = verdicts(tok, model, dev, [items[r["id"]]["text"] for r in R], pid, nid)
    y = np.array([r["gold"] for r in R])
    p0 = np.array([r["p_pos"] for r in R])
    return dict(n=len(R), auroc_before=gc.auc(y, p0), auroc_after=gc.auc(y, p),
                says_pos_before=float((p0 > .5).mean()), says_pos_after=float((p > .5).mean()),
                verdict_unchanged=float(((p0 > .5) == (p > .5)).mean()))


def final(a):
    import torch
    from safetensors.torch import save_file
    recs, z, tok, model, dev, u, scale, pos_id, neg_id = load()
    rows = json.loads((OUT / "tune_dev_all.json").read_text())
    # Selection rule (fixed before looking at test): ranking alone is not a fixed judge if it still calls most
    # answers bad, so take the best balanced accuracy among settings within 0.05 of the best same-source AUROC.
    top = max(r["auroc_same_source"] for r in rows)
    best = max((r for r in rows if r["auroc_same_source"] >= top - 0.05), key=lambda r: r["bal_acc"])
    b, n, al = best["block"], best["n"], best["alpha"]
    print(f"chosen on dev: block {b}, N={n}, alpha={al} ({best['n_weights']} weights)", flush=True)
    S = np.load(OUT / "acts.npz")
    tr = np.array([recs[i]["split"] == "train" for i in S["idx"]])
    idx, k = fit_key(S[f"b{b}"], z[S["idx"]], n, tr)
    T = [r for r in recs if r["split"] == "test"]
    y = np.array([r["gold"] for r in T])
    strata = np.array([r["stratum"] for r in T])
    groups = np.array([r["group"] for r in T])
    pv = np.array([r["p_pos"] for r in T])
    res = dict(chosen=dict(block=b, n=n, alpha=al), total_params=sum(p.numel() for p in model.parameters()))
    t = time.time()
    res["text_loss_before"] = wikitext_loss(tok, model, dev)
    res["generations_before"] = generations(tok, model, dev)
    print(f"  baseline text loss {res['text_loss_before']:.3f} ({time.time() - t:.0f}s)", flush=True)
    L = BLOCKS[b]
    with Edit(model, b, idx, k, u[L], scale[L], al) as e:
        res.update(n_weights=e.n_weights, frac_weights=e.n_weights / res["total_params"], bf16_rel_err=e.rel_err)
        p = verdicts(tok, model, dev, [r["text"] for r in T], pos_id, neg_id)
        res["rb2safety_test"] = dict(before=s1.metrics(y, pv, strata), after=s1.metrics(y, p, strata))
        ci, diff = gc.boot(y, {"verdict": pv, "edited": p}, groups)
        res["rb2safety_test"]["after"]["auroc_ci"] = ci["edited"]
        res["rb2safety_test"]["gain_ci"] = diff["edited"]
        print(f"  RB2 Safety test: {res['rb2safety_test']}", flush=True)
        for bench in ("bff", "judgebench"):
            res[bench] = other_bench(tok, model, dev, bench)
            print(f"  {bench}: {res[bench]}", flush=True)
        res["text_loss_after"] = wikitext_loss(tok, model, dev)
        res["generations_after"] = generations(tok, model, dev)
        print(f"  text loss {res['text_loss_before']:.3f} -> {res['text_loss_after']:.3f}", flush=True)
        W = mlp(model, b).down_proj.weight
        delta = (W[:, e.idx].float() - e.orig.float()).cpu().contiguous()
        save_file({"delta": delta, "columns": torch.as_tensor(idx).cpu()},
                  str(HERE / "results" / "step2_edit_diff.safetensors"),
                  metadata=dict(model=smoke.MODEL, tensor=f"model.language_model.layers.{b}.mlp.down_proj.weight",
                                note="add delta (float32) to these columns, then cast back to bf16"))
    np.save(OUT / "test_p_edited.npy", p)
    (HERE / "results" / "step2_final.json").write_text(json.dumps(res, indent=1))
    print("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["acts", "tune", "ablate", "final"])
    a = ap.parse_args()
    dict(acts=acts, tune=tune, ablate=ablate, final=final)[a.cmd](a)
