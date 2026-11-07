#!/usr/bin/env python3
"""
Full gap check (Phase 3): does Qwen3.5-0.8B's hidden state know more than its verdict says, on held-out items,
beyond what surface features explain?

Benchmarks (all items, forced verdict, thinking off, same prompts as smoke.py):
  bff         every real BFF answer with a unanimous expert label, no reference
  judgebench  all 350 GPT-4o pairs, both orders
  rb2safety   every RewardBench 2 Safety prompt: first chosen + first rejected response

Splits: by question / pair / prompt, 60% train, 20% dev, 20% test, fixed by a hash of the group id and saved to
results/splits_<bench>.json, so later phases (steering, edits, the Claude editor) use exactly the same split.
Probe: logistic regression on one layer's residual stream at the verdict position; layer and C chosen on dev,
scored once on test. CIs: 2,000 bootstrap resamples of test groups.

  .venv/bin/python experiments/weight_space/gap_check.py run
  .venv/bin/python experiments/weight_space/gap_check.py analyze
"""
import argparse, ast, hashlib, json, re, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import smoke  # noqa: E402

RAW = HERE / "results" / "raw" / "gap"
RES = HERE / "results"
REFUSAL = re.compile(r"\b(I can(?:'|’|no)t|I won(?:'|’)t|I'm sorry|I am sorry|I apologi[sz]e|cannot (?:help|assist|provide)|"
                     r"not able to|unable to|I must decline|against (?:my|the) (?:guidelines|policy))", re.I)


def split_of(group):
    h = int(hashlib.sha256(group.encode()).hexdigest(), 16) % 100
    return "train" if h < 60 else "dev" if h < 80 else "test"


# ----------------------------------------------------------------------------- items (all of them)
def items_bff():
    from run_jev_bff import load_data, _to_list
    v, _ = load_data(None, None)
    v = v[v["dataset"].astype(str).str.lower() == "bffbench"]
    out = []
    for (qid, cid, turn, model), g in v.groupby(["qid", "cid", "turn", "model"]):
        labs = [str(x).lower() for x in g["label"]]
        if len(set(labs)) != 1 or labs[0] not in ("correct", "incorrect"):
            continue
        conv = [{"role": m["role"], "content": m["content"]} for m in _to_list(g.iloc[0]["conv"])]
        out.append(dict(id=f"bff|{cid}-t{turn}|{model}", group=str(qid), gold=int(labs[0] == "correct"),
                        examinee=str(model), turn=int(turn), answer_chars=len(conv[-1]["content"]),
                        text=smoke.BFF_JUDGE.format(conversation=smoke.render_conv(conv), reference="")))
    return sorted(out, key=lambda x: x["id"])


def items_judgebench():
    from loaders import load_judgebench
    out = []
    for it in load_judgebench():
        out.append(dict(id=f"jb|{it['id']}", group=str(it["group"]), gold=it["gold"], order=it["order"],
                        pair=str(it["pair_id"]), category=it["category"],
                        len_a=len(it["resp_a"]), len_b=len(it["resp_b"]),
                        text=smoke.PAIR_JUDGE.format(question=it["question"], a=it["resp_a"], b=it["resp_b"])))
    return out


def items_rb2safety():
    from datasets import load_dataset
    out = []
    for r in load_dataset("allenai/reward-bench-2", split="test"):
        if r["subset"] != "Safety":
            continue
        models = r["models"] if isinstance(r["models"], list) else ast.literal_eval(str(r["models"]))
        for g, resp, mi in ((1, r["chosen"][0], 0), (0, r["rejected"][0], len(r["chosen"]))):
            resp = str(resp)
            out.append(dict(id=f"rb2s|{r['id']}|{g}", group=str(r["id"]), gold=g, resp_chars=len(resp),
                            refusal=int(bool(REFUSAL.search(resp[:500]))),
                            resp_model=str(models[mi]) if mi < len(models) else "unknown",
                            text=smoke.SINGLE_JUDGE.format(prompt=str(r["prompt"]), response=resp)))
    return out


LOADERS = {"bff": items_bff, "judgebench": items_judgebench, "rb2safety": items_rb2safety}


def run(a):
    tok, model, dev = smoke.load_model()
    for bench in a.bench:
        items = LOADERS[bench]()
        for it in items:
            it["split"] = split_of(it["group"])
        RES.mkdir(exist_ok=True)
        (RES / f"splits_{bench}.json").write_text(json.dumps(
            {s: sorted({it["group"] for it in items if it["split"] == s}) for s in ("train", "dev", "test")}, indent=0))
        smoke.forward(tok, model, dev, bench, items, RAW / bench, a.max_len)


# ----------------------------------------------------------------------------- analysis
def auc(y, s):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s)) if len(set(y)) == 2 else float("nan")


def boot(y, scores, groups, n=2000, seed=0):
    """Bootstrap over groups. scores: dict name -> array. Returns per-name (lo, hi) and paired diffs vs 'verdict'."""
    rng = np.random.default_rng(seed)
    ug = np.unique(groups)
    rows = {g: np.where(groups == g)[0] for g in ug}
    res = {k: [] for k in scores}
    for _ in range(n):
        ix = np.concatenate([rows[g] for g in rng.choice(ug, len(ug))])
        if len(set(y[ix])) < 2:
            continue
        for k, s in scores.items():
            res[k].append(auc(y[ix], s[ix]))
    ci = {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in res.items()}
    diff = {k: (float(np.percentile(np.subtract(v, res["verdict"]), 2.5)),
                float(np.percentile(np.subtract(v, res["verdict"]), 97.5))) for k, v in res.items() if k != "verdict"}
    return ci, diff


def fit_probe(X, y, sp):
    """Pick (layer, C) on dev; return test scores, chosen layer/C, dev AUROC per layer, and the fitted model."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    tr, dv, te = (sp == "train"), (sp == "dev"), (sp == "test")
    best, dev_by_layer = None, []
    for l in range(X.shape[1]):
        lb = 0
        for C in (0.003, 0.03, 0.3):
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000)).fit(X[tr, l], y[tr])
            d = auc(y[dv], clf.predict_proba(X[dv, l])[:, 1])
            lb = max(lb, d)
            if best is None or d > best[0]:
                best = (d, l, C, clf)
        dev_by_layer.append(round(lb, 3))
    d, l, C, clf = best
    # refit on train + dev at the chosen layer and C, score test once
    trdv = tr | dv
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000)).fit(X[trdv, l], y[trdv])
    return clf.predict_proba(X[:, l])[:, 1], l, C, dev_by_layer, clf


def surface_scores(F, y, sp):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    trdv = sp != "test"
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)).fit(F[trdv], y[trdv]).predict_proba(F)[:, 1]


def combined(F, probe, y, sp):
    """Surface features + probe score, fit on dev (probe scores on train are in-sample), scored on test."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    Z = np.hstack([F, np.log(probe / (1 - probe + 1e-9) + 1e-9)[:, None]])
    dv = sp == "dev"
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)).fit(Z[dv], y[dv]).predict_proba(Z)[:, 1]


def strat_auc(y, s, strata, mask):
    vals, ws = [], []
    for k in np.unique(strata[mask]):
        m = mask & (strata == k)
        if len(set(y[m])) == 2:
            vals.append(auc(y[m], s[m])), ws.append(m.sum())
    return float(np.average(vals, weights=ws)) if vals else float("nan"), len(vals)


def analyze(a):
    import pandas as pd
    out, lines = {}, ["# Gap check: Qwen3.5-0.8B, forced verdict, thinking off (held-out test split)", "",
                      "Probe layer and regularization chosen on dev, refit on train+dev, scored once on test. "
                      "95% CIs: bootstrap over test questions/pairs/prompts. Gap = probe − verdict (paired).", ""]
    for bench in a.bench:
        idx = RAW / bench / "index.jsonl"
        if not idx.exists():
            continue
        recs = [json.loads(l) for l in open(idx)]
        y = np.array([r["gold"] for r in recs])
        sp = np.array([r["split"] for r in recs])
        groups = np.array([r["group"] for r in recs])
        p = np.array([r["p_pos"] for r in recs])
        lens = np.array([r["lens_p"] for r in recs])
        X = np.stack([np.load(RAW / bench / r["file"]).astype(np.float32) for r in recs])
        te = sp == "test"
        probe, layer, C, dev_by_layer, _ = fit_probe(X, y, sp)
        dv = sp == "dev"
        lens_layer = int(np.nanargmax([auc(y[dv], lens[dv, l]) for l in range(lens.shape[1])]))
        ntok = np.log([r["n_tokens"] for r in recs])
        if bench == "bff":
            ex = pd.get_dummies(pd.Series([r["examinee"] for r in recs])).values.astype(float)
            F = np.hstack([ex, ntok[:, None], np.log([r["answer_chars"] for r in recs])[:, None],
                           np.array([r["turn"] for r in recs])[:, None]])
            strata, sname = np.array([r["examinee"] for r in recs]), "within answer model"
        elif bench == "rb2safety":
            if "resp_model" not in recs[0]:  # runs made before resp_model was stored
                rm = {it["id"]: it["resp_model"] for it in items_rb2safety()}
                for r in recs:
                    r["resp_model"] = rm[r["id"]]
            mods = pd.Series([r["resp_model"] for r in recs])
            mods = mods.where(mods.map(mods.value_counts()) >= 5, "other")  # pool rare models
            F = np.column_stack([np.array([r["refusal"] for r in recs]), ntok, np.log([r["resp_chars"] for r in recs]),
                                 pd.get_dummies(mods).values.astype(float)])
            # the response model nearly decides the label, so compare within models that wrote both kinds
            strata = np.array([f"{r['resp_model']}|{r['refusal']}" for r in recs])
            sname = "within response model x refusal (strata with both labels)"
        else:
            F = np.column_stack([np.array([r["order"] for r in recs]),
                                 np.log([r["len_a"] / r["len_b"] for r in recs])])
            strata, sname = np.array([r["category"] for r in recs]), "within category"
        surf = surface_scores(F, y, sp)
        comb = combined(F, probe, y, sp)
        scores = {"verdict": p, "lens": lens[:, lens_layer], "probe": probe, "surface": surf, "surface+probe": comb}
        ci, diff = boot(y[te], {k: v[te] for k, v in scores.items()}, groups[te])
        s = dict(n=len(y), n_test=int(te.sum()), test_groups=int(len(set(groups[te]))), pos_rate=float(y.mean()),
                 says_pos_test=float((p[te] > 0.5).mean()), acc_test=float(((p[te] > 0.5) == y[te]).mean()),
                 probe_layer=layer, probe_C=C, lens_layer=lens_layer, probe_dev_auroc_by_layer=dev_by_layer,
                 truncated=int(sum(r["truncated"] for r in recs)))
        for k, v in scores.items():
            s[f"{k}_auroc"] = auc(y[te], v[te])
            s[f"{k}_ci"] = ci[k]
            if k in diff:
                s[f"{k}_minus_verdict_ci"] = diff[k]
        s["strat_name"] = sname
        s["lens_dev_auroc_by_layer"] = [round(auc(y[dv], lens[dv, l]), 3) for l in range(lens.shape[1])]
        bins = np.linspace(0, 1, 11)
        s["p_hist"] = {str(g): np.histogram(p[y == g], bins)[0].tolist() for g in (0, 1)}
        s["verdict_strat"], s["n_strata"] = strat_auc(y, p, strata, te)
        s["probe_strat"], _ = strat_auc(y, probe, strata, te)
        # more power: 5-fold CV over ALL groups at the dev-chosen layer/C (surface model refit per fold too)
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import GroupKFold
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        oof_p, oof_s = np.zeros(len(y)), np.zeros(len(y))
        for tr, tt in GroupKFold(5).split(X, y, groups):
            oof_p[tt] = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000)).fit(
                X[tr, layer], y[tr]).predict_proba(X[tt, layer])[:, 1]
            oof_s[tt] = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)).fit(
                F[tr], y[tr]).predict_proba(F[tt])[:, 1]
        allm = np.ones(len(y), bool)
        s["cv_all"] = dict(verdict=auc(y, p), probe=auc(y, oof_p), surface=auc(y, oof_s),
                           verdict_strat=strat_auc(y, p, strata, allm)[0], probe_strat=strat_auc(y, oof_p, strata, allm)[0],
                           surface_strat=strat_auc(y, oof_s, strata, allm)[0])
        if bench == "judgebench":
            by = {}
            for r, pr in zip(recs, p):
                by.setdefault(r["pair"], {})[r["order"]] = (pr, r["gold"], r["split"])
            full = [v for v in by.values() if len(v) == 2 and v[0][2] == "test"]
            s["same_slot_both_orders"] = float(np.mean([(v[0][0] > .5) == (v[1][0] > .5) for v in full]))
            s["says_A_test"] = float((p[te] > 0.5).mean())
            # position-debiased verdict: average P(first better) over the two orders (removing a constant A bias)
            yd = np.array([v[0][1] for v in full])
            sd = np.array([(v[0][0] + 1 - v[1][0]) / 2 for v in full])
            s["debiased_pair_auroc"] = auc(yd, sd)
            s["debiased_pair_acc"] = float(((sd > .5) == yd).mean())
            s["test_pairs"] = len(full)
        out[bench] = s
        f = lambda k: f"{s[k + '_auroc']:.2f} [{s[k + '_ci'][0]:.2f}, {s[k + '_ci'][1]:.2f}]"
        lines += [f"## {bench}", "",
                  f"{s['n']} items ({s['pos_rate']:.0%} positive); test {s['n_test']} items from {s['test_groups']} "
                  f"groups; {s['truncated']} truncated. Verdict says positive {s['says_pos_test']:.0%} of test items, "
                  f"accuracy {s['acc_test']:.0%}.", "",
                  "| Score | Test AUROC [95% CI] | minus verdict [95% CI] |", "|---|---|---|"]
        for k, nm in (("verdict", "Verdict P(positive)"), ("lens", f"Logit lens, layer {lens_layer}"),
                      ("probe", f"Hidden-state probe, layer {layer}"), ("surface", "Surface features only"),
                      ("surface+probe", "Surface features + probe")):
            dd = f"{s[k + '_minus_verdict_ci'][0]:+.2f} to {s[k + '_minus_verdict_ci'][1]:+.2f}" if k != "verdict" else ""
            lines.append(f"| {nm} | {f(k)} | {dd} |")
        cv = s["cv_all"]
        lines += ["", f"- {sname} ({s['n_strata']} strata, test): verdict {s['verdict_strat']:.2f}, "
                      f"probe {s['probe_strat']:.2f}",
                  f"- All items, 5-fold CV grouped by question/pair/prompt (layer {layer}): verdict {cv['verdict']:.2f}, "
                  f"probe {cv['probe']:.2f}, surface {cv['surface']:.2f}; {sname}: verdict {cv['verdict_strat']:.2f}, "
                  f"probe {cv['probe_strat']:.2f}, surface {cv['surface_strat']:.2f}"]
        if bench == "judgebench":
            lines += [f"- Position bias (test pairs): same slot picked in both orders for {s['same_slot_both_orders']:.0%}"
                      f" of {s['test_pairs']} pairs; says A for {s['says_A_test']:.0%} of test items",
                      f"- Verdict averaged over both orders (constant A bias removed): AUROC {s['debiased_pair_auroc']:.2f},"
                      f" accuracy {s['debiased_pair_acc']:.0%}"]
        lines += [f"- Probe dev AUROC by layer (0 = embeddings): {' '.join(f'{x:.2f}' for x in dev_by_layer)}", ""]
    (RES / "gap_summary.md").write_text("\n".join(lines))
    (RES / "gap_summary.json").write_text(json.dumps(out, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--bench", nargs="+", default=["rb2safety", "bff", "judgebench"])
    ap.add_argument("--max-len", type=int, default=8192)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else analyze(a)
