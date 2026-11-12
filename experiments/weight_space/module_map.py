#!/usr/bin/env python3
"""
Module map (drill-down Step 1): which attention heads and MLPs build the Safety "knows" signal in Qwen3.5-0.8B?

Every layer adds two outputs to the residual stream: the token mixer (attention: 8 heads in layers 4, 8, 12, 16, 20,
24; linear attention: 16 heads elsewhere) and the MLP (3,584 neurons). The residual at layer R is exactly
embedding + the sum of those outputs, so a linear probe's score at R splits exactly into one share per head / MLP.

Measure A (contribution): cross-fitted probe direction w at the reference layer R (best layer of a same-source CV
  probe). For each component c, s_c = w . (its output). Its contribution = the within-strata difference in mean s_c
  between good and bad responses; share = contribution / total over all components and the embedding.
  Significance: 500 label shuffles within each question; a component is significant when its contribution beats the
  99th percentile of the largest shuffled contribution of any component (family-wise).
Measure B (standalone readout): a probe on the component's own output alone (head: its slice of the mixer output;
  MLP: its 3,584 activations), same-source 5-fold CV AUROC, for all 24 layers. Null: the same with shuffled labels.
Neurons: per-neuron contribution in the strongest MLPs, with a shuffle null, marking the 256 neurons edited in Step 2.

Benchmarks: RewardBench 2 Safety (900 items, team safety prompt) and BFF (459 items, team finance prompt).
Forward passes on a Modal GPU; analysis on the Mac.

  .venv/bin/python experiments/weight_space/module_map.py build
  modal run experiments/weight_space/module_map.py --limit 8          # smoke test
  modal run experiments/weight_space/module_map.py
  .venv/bin/python experiments/weight_space/module_map.py analyze
"""
import argparse, json, sys
from pathlib import Path

try:
    import modal
except ImportError:
    modal = None

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "raw" / "module_map"
CONDS = {"safety": "rb2safety", "bff": "bff"}


# ----------------------------------------------------------------------------- record (Modal GPU)
def record_remote(cond: str, items: list, tag: str) -> str:
    import numpy as np
    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer
    sys.path.insert(0, "/root/repo/experiments/weight_space")
    import smoke
    tok = AutoTokenizer.from_pretrained(smoke.MODEL)
    model = AutoModelForImageTextToText.from_pretrained(smoke.MODEL, dtype=torch.bfloat16).to("cuda").eval()
    lm = model.model.language_model
    n = len(lm.layers)
    grab = {}

    def pre(key):
        def f(mod, args):
            grab[key] = args[0][0, -1].float().cpu()
        return f
    for i, L in enumerate(lm.layers):
        mix = L.linear_attn.out_proj if hasattr(L, "linear_attn") else L.self_attn.o_proj
        mix.register_forward_pre_hook(pre(("mix", i)))
        L.mlp.down_proj.register_forward_pre_hook(pre(("mlp", i)))
    pos_t, neg_t = (tok.encode(w, add_special_tokens=False) for w in smoke.TOKENS[CONDS[cond]])
    N = len(items)
    MIX = np.zeros((N, n, 2048), np.float16)
    MLP = np.zeros((N, n, 3584), np.float16)
    HS = np.zeros((N, n + 1, 1024), np.float16)
    P = np.zeros(N, np.float32)
    for k, it in enumerate(items):
        prompt = tok.apply_chat_template([{"role": "user", "content": it["text"]}], tokenize=False,
                                         add_generation_prompt=True, enable_thinking=False) + "VERDICT:"
        enc = tok(prompt, return_tensors="pt", truncation=True, max_length=8192).to("cuda")
        with torch.no_grad():
            o = model(**enc, output_hidden_states=True, logits_to_keep=1, use_cache=False)
        lp = torch.log_softmax(o.logits[0, -1].float(), -1)
        P[k] = float(torch.sigmoid(lp[pos_t[0]] - lp[neg_t[0]]))
        HS[k] = torch.stack([h[0, -1] for h in o.hidden_states]).float().cpu().numpy()
        for i in range(n):
            MIX[k, i] = grab[("mix", i)].numpy()
            MLP[k, i] = grab[("mlp", i)].numpy()
        if (k + 1) % 100 == 0:
            print(f"{cond}: {k + 1}/{N}", flush=True)
    path = f"/vol/{tag}{cond}.npz"
    np.savez(path, mix=MIX, mlp=MLP, hs=HS, p=P)
    vol.commit()
    return path


def main(conds: str = "safety,bff", limit: int = 0):
    tag = "smoke_" if limit else ""
    jobs = []
    for c in conds.split(","):
        items = [json.loads(l) for l in open(OUT / c / "items.jsonl")]
        items = items[:limit] if limit else items
        print(f"{c}: {len(items)} items -> Modal", flush=True)
        jobs.append((c, record_remote.spawn(c, [{"text": it["text"]} for it in items], tag)))
    for c, job in jobs:
        path = job.get()
        dest = OUT / c / f"{tag}acts.npz"
        with open(dest, "wb") as fh:
            for chunk in vol.read_file(Path(path).name):
                fh.write(chunk)
        print(f"{c}: saved {dest} ({dest.stat().st_size / 1e6:.0f} MB)", flush=True)


if modal is not None:
    image = (modal.Image.debian_slim(python_version="3.12")
             .pip_install("torch==2.15.0", "transformers==5.22.2", "numpy==2.5.4")
             .env({"HF_HOME": "/root/.cache/huggingface"})
             .add_local_file(HERE / "smoke.py", "/root/repo/experiments/weight_space/smoke.py"))
    hf_cache = modal.Volume.from_name("dlj-hf-cache", create_if_missing=True)
    vol = modal.Volume.from_name("weight-space-module-map", create_if_missing=True)
    app = modal.App("weight-space-module-map", image=image)
    record_remote = app.function(gpu=["L4", "A10G", "L40S", "A100-40GB"], timeout=3600,
                                 volumes={"/root/.cache/huggingface": hf_cache, "/vol": vol})(record_remote)
    main = app.local_entrypoint()(main)


# ----------------------------------------------------------------------------- build items (local)
def build(a):
    sys.path.insert(0, str(HERE))
    import gap_check
    src = HERE / "results" / "raw" / "prompt_ctrl" / "rb2_safety" / "items.jsonl"   # team safety prompt
    safety = [json.loads(l) for l in open(src)]
    bff = gap_check.items_bff()                                                    # team finance prompt
    for it in bff:
        it["split"] = gap_check.split_of(it["group"])
    for c, items in (("safety", safety), ("bff", bff)):
        (OUT / c).mkdir(parents=True, exist_ok=True)
        with open(OUT / c / "items.jsonl", "w") as fh:
            for it in items:
                fh.write(json.dumps(it) + "\n")
        print(c, len(items))


# ----------------------------------------------------------------------------- analysis (local)
def layer_types():
    import glob
    cfg = json.load(open(glob.glob(str(Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3.5-0.8B/snapshots/*/config.json"))[0]))
    return cfg.get("text_config", cfg)["layer_types"]


def load_weights():
    import torch
    from transformers import AutoModelForImageTextToText
    m = AutoModelForImageTextToText.from_pretrained("Qwen/Qwen3.5-0.8B", dtype=torch.float32)
    W_mix, W_down = [], []
    for L in m.model.language_model.layers:
        mix = L.linear_attn.out_proj if hasattr(L, "linear_attn") else L.self_attn.o_proj
        W_mix.append(mix.weight.detach().numpy().copy())
        W_down.append(L.mlp.down_proj.weight.detach().numpy().copy())
    return W_mix, W_down


def analyze(a):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    sys.path.insert(0, str(HERE))
    from gap_check import strat_auc

    types = layer_types()
    nheads = [16 if t == "linear_attention" else 8 for t in types]
    W_mix, W_down = load_weights()
    edited = []
    try:
        from safetensors.numpy import load_file
        d = load_file(str(HERE / "results" / "step2_edit_diff.safetensors"))
        edited = sorted(int(j) for j in d["columns"])
        edited_layer = 17   # step2 edited lm.layers[16] (0-based), i.e. layer 17 here
    except Exception as e:
        print("no edit diff:", e)
        edited_layer = None
    out = {"layer_types": types, "nheads": nheads}
    rng = np.random.default_rng(0)
    for c in a.conds:
        items = [json.loads(l) for l in open(OUT / c / "items.jsonl")]
        Z = np.load(OUT / c / "acts.npz")
        MIX, MLP, HS, P = Z["mix"].astype(np.float32), Z["mlp"].astype(np.float32), Z["hs"].astype(np.float32), Z["p"]
        N, nL = MIX.shape[:2]
        y = np.array([it["gold"] for it in items])
        g = np.array([it["group"] for it in items])
        strata = np.array([f"{it['resp_model']}|{it['refusal']}" if c == "safety" else it["examinee"] for it in items])
        allm = np.ones(N, bool)
        folds = list(GroupKFold(5).split(HS, y, g))

        # sanity: residual = embedding + sum of mixer and MLP outputs
        recon = HS[:, 0].copy()
        errs = []
        for l in range(nL - 1):
            recon = recon + MIX[:, l] @ W_mix[l].T + MLP[:, l] @ W_down[l].T
            errs.append(float(np.linalg.norm(recon - HS[:, l + 1]) / np.linalg.norm(HS[:, l + 1])))
        print(c, "reconstruction rel. error by layer (max):", round(max(errs), 4), flush=True)

        def cv_probe(X, C=0.3):
            oof = np.zeros(N)
            for tr, te in folds:
                oof[te] = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000)).fit(
                    X[tr], y[tr]).predict_proba(X[te])[:, 1]
            return oof

        curve = [round(strat_auc(y, cv_probe(HS[:, l]), strata, allm)[0], 3) for l in range(1, nL)]  # layers 1..23
        R = int(np.argmax(curve)) + 1
        print(c, "knows by layer:", curve, "ref layer", R, flush=True)

        # cross-fitted probe direction at R (raw residual space), per-item contribution scores
        comps = [("emb", 0, -1)]
        for l in range(R):
            comps += [("head", l, h) for h in range(nheads[l])] + [("mlp", l, -1)]
        S = np.zeros((N, len(comps)), np.float32)
        NEUR = {}  # per-neuron scores for every MLP layer < R: (N, 3584)
        for l in range(R):
            NEUR[l] = np.zeros((N, 3584), np.float32)
        for tr, te in folds:
            sc = StandardScaler().fit(HS[tr, R])
            lr = LogisticRegression(C=0.3, max_iter=3000).fit(sc.transform(HS[tr, R]), y[tr])
            w = lr.coef_[0] / sc.scale_
            for j, (kind, l, h) in enumerate(comps):
                if kind == "emb":
                    S[te, j] = HS[te, 0] @ w
                elif kind == "head":
                    u = W_mix[l].T @ w
                    d = MIX.shape[2] // nheads[l]
                    S[te, j] = MIX[te, l, h * d:(h + 1) * d] @ u[h * d:(h + 1) * d]
                else:
                    v = W_down[l].T @ w
                    NEUR[l][te] = MLP[te, l] * v
                    S[te, j] = NEUR[l][te].sum(1)

        # within-strata contribution, vectorized over components; label shuffles within question
        masks = [strata == k for k in np.unique(strata)]

        def contrib(M, yy):
            """size-weighted mean over strata (with both labels under yy) of mean(good) - mean(bad)."""
            tot, wsum = 0, 0
            for m in masks:
                gm, bm = m & (yy == 1), m & (yy == 0)
                if gm.any() and bm.any():
                    tot = tot + m.sum() * (M[gm].mean(0) - M[bm].mean(0))
                    wsum += m.sum()
            return tot / wsum

        grp_idx = {k: np.where(g == k)[0] for k in np.unique(g)}

        def shuffle():
            yy = y.copy()
            for ix in grp_idx.values():
                yy[ix] = rng.permutation(y[ix])
            return yy
        delta = contrib(S, y)
        total = float(delta.sum())
        shuffles = [shuffle() for _ in range(500)]
        null_max = np.array([np.abs(contrib(S, yy)).max() for yy in shuffles])
        thr = float(np.percentile(null_max, 99))
        print(c, "total", round(total, 3), "threshold share", round(thr / total, 4), flush=True)

        # measure B: standalone readout per component (all layers), plus a shuffled-label null
        yb = shuffle()

        def cv_auc(X, yy):
            oof = np.zeros(N)
            for tr, te in folds:
                oof[te] = make_pipeline(StandardScaler(), LogisticRegression(C=0.03, max_iter=2000)).fit(
                    X[tr], yy[tr]).predict_proba(X[te])[:, 1]
            return strat_auc(yy, oof, strata, allm)[0]
        cache = OUT / c / "B_cache.json"
        if cache.exists():
            B, Bnull = json.loads(cache.read_text())
        else:
            B, Bnull = {}, []
            for l in range(nL):
                d = MIX.shape[2] // nheads[l]
                for h in range(nheads[l]):
                    X = MIX[:, l, h * d:(h + 1) * d]
                    B[f"head|{l}|{h}"] = round(cv_auc(X, y), 3)
                    Bnull.append(cv_auc(X, yb))
                B[f"mlp|{l}|-1"] = round(cv_auc(MLP[:, l], y), 3)
                Bnull.append(cv_auc(MLP[:, l], yb))
                print(c, "B layer", l + 1, flush=True)
            cache.write_text(json.dumps([B, Bnull]))

        rows = []
        for j, (kind, l, h) in enumerate(comps):
            rows.append(dict(kind=kind, layer=l + 1 if kind != "emb" else 0, head=h + 1 if kind == "head" else None,
                             contrib=round(float(delta[j]), 4), share=round(float(delta[j]) / total, 4),
                             sig=bool(abs(delta[j]) > thr),
                             B=B.get(f"{kind}|{l}|{h}") if kind != "emb" else None))

        # neurons in the strongest MLPs (+ the edited layer), with a per-layer shuffle null
        mlp_rows = sorted([r for r in rows if r["kind"] == "mlp"], key=lambda r: -r["contrib"])
        show = [r["layer"] for r in mlp_rows[:2]]
        if c == "safety" and edited_layer and edited_layer not in show:
            show.append(edited_layer)
        neurons = {}
        for L1 in show:
            tot_here = total
            if L1 - 1 in NEUR:
                M = NEUR[L1 - 1]
            else:   # layer after the reference layer (the edited layer 17): use a probe read just after it
                M = np.zeros((N, 3584), np.float32)
                full = np.zeros(N, np.float32)
                for tr, te in folds:
                    sc = StandardScaler().fit(HS[tr, L1])
                    lr = LogisticRegression(C=0.3, max_iter=3000).fit(sc.transform(HS[tr, L1]), y[tr])
                    w = lr.coef_[0] / sc.scale_
                    M[te] = MLP[te, L1 - 1] * (W_down[L1 - 1].T @ w)
                    full[te] = HS[te, L1] @ w
                tot_here = float(contrib(full[:, None], y)[0])
            total_saved = total
            total = tot_here
            dn = contrib(M, y)
            nm = np.array([np.abs(contrib(M, yy)).max() for yy in shuffles[:200]])
            order = np.argsort(-dn)
            top = order[:300]
            cum = np.cumsum(np.sort(dn)[::-1])
            neurons[str(L1)] = dict(
                sorted=[round(float(x) / total, 5) for x in np.sort(dn)[::-1][:400]],
                thr=round(float(np.percentile(nm, 99)) / total, 5),
                n_sig=int((np.abs(dn) > np.percentile(nm, 99)).sum()),
                share_top10=round(float(cum[9]) / total, 4), share_top50=round(float(cum[49]) / total, 4),
                share_layer=round(float(dn.sum()) / total, 4),
                top=[dict(n=int(i), share=round(float(dn[i]) / total, 4), edited=int(i) in set(edited)) for i in top[:15]],
                edited_rank=sorted(int(np.where(order == e)[0][0]) for e in edited) if L1 == edited_layer else [],
                ref="own probe just after this layer" if L1 - 1 not in NEUR else f"layer {R} probe",
            )
            total = total_saved
        out[c] = dict(n=N, ref_layer=R, knows_curve=curve, says=round(strat_auc(y, P, strata, allm)[0], 3),
                      recon_err=round(max(errs), 4), total=round(total, 4), thr_share=round(thr / total, 4),
                      B_null_max=round(max(Bnull), 3), B_null_mean=round(float(np.mean(Bnull)), 3),
                      rows=rows, neurons=neurons, edited_layer=edited_layer, n_edited=len(edited))
        sig = [r for r in rows if r["sig"]]
        print(c, "significant components:", len(sig), "top:",
              [(r["kind"], r["layer"], r["head"], r["share"]) for r in sorted(rows, key=lambda r: -r["contrib"])[:8]],
              flush=True)
    (HERE / "results" / "module_map.json").write_text(json.dumps(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    an = sub.add_parser("analyze")
    an.add_argument("--conds", nargs="+", default=list(CONDS))
    a = ap.parse_args()
    {"build": build, "analyze": analyze}[a.cmd](a)
