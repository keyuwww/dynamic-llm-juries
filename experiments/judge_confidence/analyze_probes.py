#!/usr/bin/env python3
"""
Analyse the Modal hidden-state runs (probe_modal.py) for every model that has data.

Probes are L2 logistic regressions on one layer's residual stream, 5-fold cross-validated with folds grouped by
question (no question in both train and test); AUROC is computed on the pooled out-of-fold scores. The best layer
is chosen on the same folds, so best-layer numbers are slightly optimistic; the full curve is saved.

  real      A. "this answer is wrong" (unanimous expert label) at the answer end and at the verdict, vs the model's
               own verdict P(INCORRECT)
            B. "the experts split on this answer" at the verdict (ambiguity), on all 960 answers
            C. among answers all experts marked wrong: does the error probe score separate the ones the strong
               Tinker judges confidently ACCEPTED (all 5 samples CORRECT) from the ones they caught?
  question  "can I solve this" read-out before any answer is shown: predicts (i) this model's own verdict error and
            (ii) gpt-oss-120b's majority-verdict error on the answer that follows
  planted   "contains a planted error" at the edit, the answer end and the verdict, per variant type

Output: results/probes_modal.json and results/probes_modal.md

  python experiments/judge_confidence/analyze_probes.py
"""
import collections, json

import numpy as np

from jc_common import HERE, RAW

ROOT = RAW / "activations_modal"


def load(model, task, cond=None, pos=None):
    d = ROOT / model / task
    if not (d / "index.jsonl").exists():
        return None, None
    rows = [json.loads(l) for l in open(d / "index.jsonl")]
    if cond:
        rows = [r for r in rows if r["condition"] == cond]
    X, keep = [], []
    for r in rows:
        names = list(r["positions"])
        if pos == "target":
            ks = [k for k in names if k.startswith("target:")]
            if not ks:
                continue
            j = names.index(ks[0])
        else:
            if pos not in names:
                continue
            j = names.index(pos)
        X.append(np.load(d / r["file"])[j].astype(np.float32)), keep.append(r)
    return (np.stack(X) if X else None), keep


def cv_layers(X, y, groups, layers=None, C=0.05):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler
    layers = layers if layers is not None else range(X.shape[1])
    aucs, preds = {}, {}
    for L in layers:
        pred = np.zeros(len(y))
        for tr, te in GroupKFold(n_splits=5).split(X[:, L], y, groups):
            sc = StandardScaler().fit(X[tr, L])
            clf = LogisticRegression(C=C, max_iter=3000).fit(sc.transform(X[tr, L]), y[tr])
            pred[te] = clf.predict_proba(sc.transform(X[te, L]))[:, 1]
        aucs[L], preds[L] = float(roc_auc_score(y, pred)), pred
    best = max(aucs, key=aucs.get)
    return dict(auroc_by_layer=[aucs[L] for L in sorted(aucs)], layers=sorted(aucs), best_layer=int(best),
                best_auroc=aucs[best]), preds[best]


def auc(y, s):
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y)
    return float(roc_auc_score(y, s)) if 0 < y.mean() < 1 else None


def within(y, s, groups):
    """AUROC computed inside each answer model, averaged with weights = number of (wrong, right) pairs.
    Removes the part of the signal that only says which model wrote the answer."""
    num = den = 0.0
    for gname in set(groups):
        m = groups == gname
        yy = y[m]
        if 0 < yy.mean() < 1:
            w = yy.sum() * (1 - yy).sum()
            num += w * auc(yy, s[m])
            den += w
    return num / den if den else None


def baseline(rows, lab, y, g):
    """Cross-validated AUROC of answer model + log length alone."""
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    X = pd.get_dummies(pd.Series([rows[i]["examinee"] for i in lab]), dtype=float)
    X["len"] = np.log([rows[i]["n_tokens"] for i in lab])
    pred = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, g):
        pred[te] = LogisticRegression(max_iter=2000).fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])[:, 1]
    return auc(y, pred)


def tinker_votes(cond="none"):
    rows = [json.loads(l) for l in open(RAW / "judgments_real.jsonl")]
    v = collections.defaultdict(dict)
    for r in rows:
        if r["condition"] == cond and r["vote_share"] is not None:
            v[r["item_id"]][r["judge"]] = r["vote_share"]
    return v


def analyze_model(m):
    res = {}
    layers = None
    tv = tinker_votes("none")
    # ---------------------------------------------------------------- real
    for cond in ("none", "human"):
        out = {}
        for pos in ("end", "verdict"):
            X, rows = load(m, "real", cond, pos)
            if X is None:
                continue
            layers = layers or list(range(0, X.shape[1], 2)) + ([X.shape[1] - 1] if (X.shape[1] - 1) % 2 else [])
            lab = [i for i, r in enumerate(rows) if r["gold_unanimous"] in (0, 1)]
            y = np.array([1 - rows[i]["gold_unanimous"] for i in lab])
            g = np.array([rows[i]["qid"] for i in lab])
            curve, pred = cv_layers(X[lab], y, g, layers)
            verdict = auc(y, [1 - rows[i]["p_correct"] for i in lab])
            ex = np.array([rows[i]["examinee"] for i in lab])
            pv = np.array([1 - rows[i]["p_correct"] for i in lab])
            out[f"error@{pos}"] = dict(curve, verdict_auroc=verdict, n=len(lab),
                                       within_model_probe=within(y, pred, ex), within_model_verdict=within(y, pv, ex),
                                       baseline_model_len=baseline(rows, lab, y, g))
            if pos == "verdict" and cond == "none":
                # C. the strong judges' confident misses among wrong answers
                wrong = [k for k, i in enumerate(lab) if rows[i]["gold_unanimous"] == 0]
                for j in ("gpt-oss-120b", "qwen3.6-35b-a3b", "deepseek-v3.1"):
                    ids = [(k, tv.get(rows[lab[k]]["item_id"], {}).get(j)) for k in wrong]
                    ids = [(k, s) for k, s in ids if s is not None]
                    yy = [int(s == 1.0) for _, s in ids]  # 1 = judge confidently accepted the wrong answer
                    out[f"flags_missed_by_{j}"] = dict(
                        n_wrong=len(ids), n_missed=int(sum(yy)),
                        probe_auroc=auc(yy, [-pred[k] for k, _ in ids]),
                        verdict_auroc=auc(yy, [rows[lab[k]]["p_correct"] for k, _ in ids]),
                        probe_mean_missed=float(np.mean([pred[k] for k, s in ids if s == 1.0])) if sum(yy) else None,
                        probe_mean_caught=float(np.mean([pred[k] for k, s in ids if s != 1.0])))
                # B. human split (ambiguity) on all answers
                ys = np.array([int(r["gold_unanimous"] is None) for r in rows])
                curve_s, _ = cv_layers(X, ys, np.array([r["qid"] for r in rows]), layers)
                out["split@verdict"] = dict(curve_s, verdict_extremeness_auroc=auc(
                    ys, [-abs(r["p_correct"] - 0.5) for r in rows]), n=len(rows), n_split=int(ys.sum()))
        if out:
            res[f"real_{cond}"] = out
    # ---------------------------------------------------------------- question
    X, rows = load(m, "question", "question", "last")
    if X is not None:
        layers = layers or list(range(0, X.shape[1], 2))
        own = {}
        idx = ROOT / m / "real" / "index.jsonl"
        if idx.exists():
            for l in open(idx):
                r = json.loads(l)
                if r["condition"] == "none" and r["gold_unanimous"] in (0, 1):
                    own[r["item_id"]] = int((r["p_correct"] >= 0.5) != (r["gold_unanimous"] == 1))
        out = {}
        for name, lab_fn in (("own_verdict_error", lambda r: own.get(r["item_id"])),
                             ("gptoss_error", lambda r: None if r["gold_unanimous"] not in (0, 1) or
                              tv.get(r["item_id"], {}).get("gpt-oss-120b") is None else
                              int((tv[r["item_id"]]["gpt-oss-120b"] >= 0.5) != (r["gold_unanimous"] == 1)))):
            lab = [(i, lab_fn(r)) for i, r in enumerate(rows)]
            lab = [(i, v) for i, v in lab if v is not None]
            if len(lab) < 50:
                continue
            y = np.array([v for _, v in lab])
            curve, _ = cv_layers(X[[i for i, _ in lab]], y, np.array([rows[i]["qid"] for i, _ in lab]), layers)
            out[name] = dict(curve, n=len(lab), positives=int(y.sum()))
        res["question"] = out
    # ---------------------------------------------------------------- planted
    for cond in ("none", "human"):
        out = {}
        for pos in ("target", "end", "verdict"):
            X, rows = load(m, "planted", cond, pos)
            if X is None:
                continue
            layers = layers or list(range(0, X.shape[1], 2))
            y = np.array([1 - r["gold"] for r in rows])
            curve, pred = cv_layers(X, y, np.array([r["item_id"] for r in rows]), layers)
            vt = np.array([r["vtype"] for r in rows])
            pv = np.array([1 - r["p_correct"] for r in rows])
            per = {}
            for t in sorted(set(vt) - {"ORIG"}):
                mm = (vt == t) | (vt == "ORIG")
                yt = (vt[mm] == t).astype(int)
                per[t] = dict(n=int((vt == t).sum()), probe=auc(yt, pred[mm]), verdict=auc(yt, pv[mm]))
            out[f"planted@{pos}"] = dict(curve, verdict_auroc=auc(y, pv), by_type=per, n=len(rows))
        if out:
            res[f"planted_{cond}"] = out
    return res


def fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def main():
    models = sorted(p.name for p in ROOT.iterdir() if p.is_dir()) if ROOT.exists() else []
    allres = {m: analyze_model(m) for m in models}
    (HERE / "results" / "probes_modal.json").write_text(json.dumps(allres, indent=1))
    L = ["# Hidden-state probes on Modal (all models)", "",
         "Probe = logistic regression on one layer, 5-fold CV grouped by question; best layer chosen on the same folds "
         "(slightly optimistic). Verdict = the model's own P(INCORRECT) after a forced \"VERDICT:\" with no reasoning.", ""]
    for m, res in allres.items():
        L += [f"## {m}", ""]
        for cond in ("none", "human"):
            r = res.get(f"real_{cond}")
            if not r:
                continue
            L += [f"**Real BFF answers, {'no reference' if cond == 'none' else 'with reference'}**", "",
                  "Within model = AUROC computed inside each answer model and averaged, which removes the 'who wrote it' "
                  "signal; baseline = answer model + length alone.", "",
                  "| Read-out | n | Verdict AUROC | Probe AUROC (best layer) | Verdict, within model | Probe, within model | Baseline |",
                  "|---|---|---|---|---|---|---|"]
            for k in ("error@end", "error@verdict"):
                if k in r:
                    L.append(f"| answer is wrong, {k.split('@')[1]} | {r[k]['n']} | {fmt(r[k]['verdict_auroc'])} | "
                             f"{fmt(r[k]['best_auroc'])} (L{r[k]['best_layer']}) | {fmt(r[k].get('within_model_verdict'))} | "
                             f"{fmt(r[k].get('within_model_probe'))} | {fmt(r[k].get('baseline_model_len'))} |")
            if "split@verdict" in r:
                s = r["split@verdict"]
                L.append(f"| experts split ({s['n_split']} of {s['n']}) | {s['n']} | {fmt(s['verdict_extremeness_auroc'])} "
                         f"(verdict near 50%) | {fmt(s['best_auroc'])} (L{s['best_layer']}) | | | |")
            L.append("")
            fl = [(k, v) for k, v in r.items() if k.startswith("flags_missed_by_")]
            if fl:
                L += ["Shared blind spot: among answers all experts marked wrong, do the ones a strong judge confidently "
                      "ACCEPTED also look more correct to this small model? AUROC of the small model's 'looks correct' "
                      "score (probe or verdict) for accepted vs caught; 0.5 = no relation, above 0.5 = the small model "
                      "shares the blind spot.", "",
                      "| Strong judge | Wrong answers | Confidently accepted | Probe | Small model's verdict |",
                      "|---|---|---|---|---|"]
                for k, v in fl:
                    L.append(f"| {k.replace('flags_missed_by_', '')} | {v['n_wrong']} | {v['n_missed']} | "
                             f"{fmt(v['probe_auroc'])} | {fmt(v['verdict_auroc'])} |")
                L.append("")
        q = res.get("question")
        if q:
            L += ["**Question only (before any answer is shown)**", "", "| Predicts | n | Positives | Probe AUROC |",
                  "|---|---|---|---|"]
            for k, v in q.items():
                L.append(f"| {k.replace('_', ' ')} | {v['n']} | {v['positives']} | {fmt(v['best_auroc'])} (L{v['best_layer']}) |")
            L.append("")
        for cond in ("none", "human"):
            r = res.get(f"planted_{cond}")
            if not r:
                continue
            L += [f"**Planted errors, {'no reference' if cond == 'none' else 'with reference'}**", "",
                  "| Position | n | Verdict AUROC | Probe AUROC |", "|---|---|---|---|"]
            for k, v in r.items():
                L.append(f"| {k.split('@')[1]} | {v['n']} | {fmt(v['verdict_auroc'])} | {fmt(v['best_auroc'])} (L{v['best_layer']}) |")
            v = r.get("planted@verdict")
            if v:
                L += ["", "| Type vs ORIG at verdict | n | Verdict | Probe |", "|---|---|---|---|"]
                for t, x in v["by_type"].items():
                    L.append(f"| {t} | {x['n']} | {fmt(x['verdict'])} | {fmt(x['probe'])} |")
            L.append("")
    (HERE / "results" / "probes_modal.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
