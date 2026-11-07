#!/usr/bin/env python3
"""
Step 1 on RB2 Safety: a run-time nudge (no weight changes). Can the judge's own later layers carry what it "knows"
at layer 14 through to its verdict, if we hand them the signal?

Pieces (all fitted on the TRAIN split only):
  knows   z = standardized logit of a linear probe on the layer-14 residual at the verdict position (the gap check's
          probe; layer and C from gap_summary.json). Precomputed from the stored hidden states.
  says    u_L = the direction at layer L that the model's OWN downstream computation reads as "CORRECT":
          mean gradient of logit(" COR") - logit(" INC") w.r.t. the layer-L residual at the verdict position.

Conditions (one forward pass per item; the edit touches only the verdict position):
  baseline        no change
  constant        h_L += a * |h_L| * u_L            same push for every item: shifts the bias, can't fix ranking
  knows-driven    h_L += a * |h_L| * z * u_L        push toward CORRECT in proportion to what the probe reads
  direct (offline ceiling)  verdict logit + a * z   wire the probe straight into the output score

Tuning: layer L in {14, 17, 20, 23} and strength a on DEV; the chosen settings are scored once on TEST.
Metrics: AUROC overall and within response model x refusal style (the fair comparison), says-CORRECT rate,
balanced accuracy at P = 0.5.

  .venv/bin/python experiments/weight_space/step1_nudge.py tune
  .venv/bin/python experiments/weight_space/step1_nudge.py test
"""
import argparse, json, sys, time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gap_check as gc  # noqa: E402
import smoke  # noqa: E402

BENCH = "rb2safety"
RAW = gc.RAW / BENCH
OUT = HERE / "results" / "raw" / "step1"
LAYERS = (14, 17, 20, 23)
# The verdict-position residual is small (median norm ~2-10), and a constant push of 0.05 x |h| already flips 99% of
# verdicts to CORRECT, so the grid sits low.
ALPHAS_CONST = (0.005, 0.01, 0.02, 0.05)
ALPHAS_KNOWS = (0.005, 0.01, 0.02, 0.05, 0.1, 0.2)


def load_items():
    """Stored gap-check records joined with their prompt text and response model."""
    recs = [json.loads(l) for l in open(RAW / "index.jsonl")]
    items = {it["id"]: it for it in gc.items_rb2safety()}
    for r in recs:
        r["text"] = items[r["id"]]["text"]
        r["resp_model"] = items[r["id"]]["resp_model"]
        r["stratum"] = f"{r['resp_model']}|{r['refusal']}"
    return recs


def fit_knows(recs):
    """Layer-14 probe fitted on train; returns z-scores (standardized decision function) for every item."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    s = json.loads((HERE / "results" / "gap_summary.json").read_text())[BENCH]
    layer, C = s["probe_layer"], s["probe_C"]
    X = np.stack([np.load(RAW / r["file"])[layer].astype(np.float32) for r in recs])
    y = np.array([r["gold"] for r in recs])
    tr = np.array([r["split"] == "train" for r in recs])
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000)).fit(X[tr], y[tr])
    d = clf.decision_function(X)
    z = (d - d[tr].mean()) / d[tr].std()
    return z, layer


def says_directions(tok, model, dev, recs, n=64):
    """Mean gradient of (logit COR - logit INC) w.r.t. each candidate layer's residual at the verdict position."""
    import torch
    pos_id = tok.encode(" CORRECT", add_special_tokens=False)[0]
    neg_id = tok.encode(" INCORRECT", add_special_tokens=False)[0]
    train = [r for r in recs if r["split"] == "train"][:n]
    acc = {L: torch.zeros(model.config.text_config.hidden_size, device=dev) for L in LAYERS}
    norms = {L: [] for L in LAYERS}
    for r in train:
        enc = encode(tok, r["text"], dev)
        o = model(**enc, output_hidden_states=True, logits_to_keep=1, use_cache=False)
        hs = o.hidden_states
        for L in LAYERS:
            hs[L].retain_grad()
        (o.logits[0, -1, pos_id] - o.logits[0, -1, neg_id]).float().backward()
        for L in LAYERS:
            g = hs[L].grad[0, -1].float()
            acc[L] += g / g.norm()
            norms[L].append(hs[L][0, -1].float().norm().item())
        model.zero_grad(set_to_none=True)
    return ({L: (acc[L] / acc[L].norm()).to(torch.bfloat16) for L in LAYERS},
            {L: float(np.median(norms[L])) for L in LAYERS}, pos_id, neg_id)


def encode(tok, text, dev):
    prompt = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False, add_generation_prompt=True,
                                     enable_thinking=False) + "VERDICT:"
    return tok(prompt, return_tensors="pt", truncation=True, max_length=8192).to(dev)


def run_condition(tok, model, dev, recs, z, u, scale, L, alpha, mode, pos_id, neg_id):
    """P(CORRECT) per item with h_L += alpha * scale * (z or 1) * u at the verdict position."""
    import torch
    lm = model.model.language_model
    state = {}

    def hook(_m, _inp, out):
        if state.get("vec") is not None:
            out[:, -1, :] += state["vec"]
        return out

    h = lm.layers[L - 1].register_forward_hook(hook)  # hidden_states[L] is the output of block L-1
    ps = []
    try:
        for r, zi in zip(recs, z):
            k = (zi if mode == "knows" else 1.0) * alpha * scale
            state["vec"] = (u * k).to(torch.bfloat16) if alpha else None
            enc = encode(tok, r["text"], dev)
            with torch.no_grad():
                lg = model(**enc, logits_to_keep=1, use_cache=False).logits[0, -1].float()
            ps.append(float(torch.sigmoid(lg[pos_id] - lg[neg_id])))
    finally:
        h.remove()
    return np.array(ps)


def metrics(y, p, strata):
    from sklearn.metrics import balanced_accuracy_score
    m = np.ones(len(y), bool)
    return dict(auroc=gc.auc(y, p), auroc_same_source=gc.strat_auc(y, p, strata, m)[0],
                says_correct=float((p > 0.5).mean()), bal_acc=float(balanced_accuracy_score(y, p > 0.5)))


def setup():
    recs = load_items()
    z, probe_layer = fit_knows(recs)
    tok, model, dev = smoke.load_model()
    cache = OUT / "directions.pt"
    import torch
    if cache.exists():
        d = torch.load(cache)
        u, scale, pos_id, neg_id = d["u"], d["scale"], d["pos_id"], d["neg_id"]
        u = {L: v.to(dev) for L, v in u.items()}
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        t = time.time()
        u, scale, pos_id, neg_id = says_directions(tok, model, dev, recs)
        torch.save(dict(u={L: v.cpu() for L, v in u.items()}, scale=scale, pos_id=pos_id, neg_id=neg_id), cache)
        print(f"says-directions from 64 train items in {time.time() - t:.0f}s; median |h_L|: "
              + ", ".join(f"L{L} {scale[L]:.0f}" for L in LAYERS), flush=True)
    return recs, z, probe_layer, tok, model, dev, u, scale, pos_id, neg_id


def tune(a):
    recs, z, probe_layer, tok, model, dev, u, scale, pos_id, neg_id = setup()
    sel = [i for i, r in enumerate(recs) if r["split"] == "dev"]
    R = [recs[i] for i in sel]
    y = np.array([r["gold"] for r in R])
    strata = np.array([r["stratum"] for r in R])
    zs = z[sel]
    base_logit = np.log(np.array([r["p_pos"] for r in R])) - np.log1p(-np.array([r["p_pos"] for r in R]))
    rows, out = [], OUT / "tune_dev.jsonl"
    done = {(d["mode"], d["layer"], d["alpha"]) for d in map(json.loads, open(out))} if out.exists() else set()
    rows += [json.loads(l) for l in open(out)] if out.exists() else []
    # offline ceiling: verdict logit + a * z
    for alpha in (0.5, 1, 2, 4, 8):
        rows.append(dict(mode="direct", layer=None, alpha=alpha, **metrics(y, 1 / (1 + np.exp(-(base_logit + alpha * zs))), strata)))
    # knows-driven first (the question we care about), then the constant-push control
    jobs = [("baseline", None, 0.0)] + [("knows", L, al) for L in LAYERS for al in ALPHAS_KNOWS] + \
           [("constant", L, al) for L in LAYERS for al in ALPHAS_CONST]
    t0 = time.time()
    with open(out, "a") as fh:
        for k, (mode, L, al) in enumerate(jobs):
            if (mode, L, al) in done:
                continue
            p = run_condition(tok, model, dev, R, zs, u[L or 14], scale[L or 14], L or 14, al, mode, pos_id, neg_id)
            row = dict(mode=mode, layer=L, alpha=al, **metrics(y, p, strata))
            fh.write(json.dumps(row) + "\n"), fh.flush()
            rows.append(row)
            print(f"[{k + 1}/{len(jobs)} {time.time() - t0:.0f}s] {mode:8s} L{L} a={al:<5} AUROC {row['auroc']:.3f} "
                  f"same-source {row['auroc_same_source']:.3f} says-CORRECT {row['says_correct']:.0%} "
                  f"bal-acc {row['bal_acc']:.3f}", flush=True)
    (OUT / "tune_dev_all.json").write_text(json.dumps(rows, indent=0))


def test(a):
    recs, z, probe_layer, tok, model, dev, u, scale, pos_id, neg_id = setup()
    rows = json.loads((OUT / "tune_dev_all.json").read_text())
    pick = {}
    for mode in ("constant", "knows", "direct"):
        cand = [r for r in rows if r["mode"] == mode]
        # constant can only shift the bias, so pick it on balanced accuracy; the others on same-source AUROC
        key = "bal_acc" if mode == "constant" else "auroc_same_source"
        pick[mode] = max(cand, key=lambda r: r[key])
    sel = [i for i, r in enumerate(recs) if r["split"] == "test"]
    R = [recs[i] for i in sel]
    y = np.array([r["gold"] for r in R])
    strata = np.array([r["stratum"] for r in R])
    zs = z[sel]
    pv = np.array([r["p_pos"] for r in R])
    res = dict(baseline=dict(mode="baseline", **metrics(y, pv, strata)))
    res["probe"] = dict(mode="probe (reads layer 14, not a fix)", **metrics(y, 1 / (1 + np.exp(-zs)), strata))
    d = pick["direct"]
    res["direct"] = dict(d, **metrics(y, 1 / (1 + np.exp(-(np.log(pv) - np.log1p(-pv) + d["alpha"] * zs))), strata))
    for mode in ("constant", "knows"):
        c = pick[mode]
        p = run_condition(tok, model, dev, R, zs, u[c["layer"]], scale[c["layer"]], c["layer"], c["alpha"], mode,
                          pos_id, neg_id)
        res[mode] = dict(mode=mode, layer=c["layer"], alpha=c["alpha"], **metrics(y, p, strata))
        np.save(OUT / f"test_p_{mode}.npy", p)
    # bootstrap CIs over test prompts (AUROC, and the gain over the baseline verdict)
    groups = np.array([r["group"] for r in R])
    scores = {"verdict": pv, "probe": 1 / (1 + np.exp(-zs)),
              "knows": np.load(OUT / "test_p_knows.npy"), "constant": np.load(OUT / "test_p_constant.npy")}
    ci, diff = gc.boot(y, scores, groups)
    for k, name in (("verdict", "baseline"), ("probe", "probe"), ("knows", "knows"), ("constant", "constant")):
        res[name]["auroc_ci"] = ci[k]
        if k in diff:
            res[name]["gain_over_baseline_ci"] = diff[k]
    (OUT / "test_results.json").write_text(json.dumps(res, indent=1))
    (HERE / "results" / "step1_test.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(f"{k:9s} {json.dumps({kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["tune", "test"])
    a = ap.parse_args()
    tune(a) if a.cmd == "tune" else test(a)
