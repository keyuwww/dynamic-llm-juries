"""Linear probes on the judge's hidden state at position A (before it reasons), and steering directions.

Two questions, after the two papers:
  1. "Is this right?" direction (Representation-as-a-Judge / INSPECTOR). Does a linear probe on the hidden
     state predict whether the candidate is correct, at which layer, and better than the judge's own
     verdict? On the anchoring errors (wrong answers that match the judge's own answer), does the probe
     still say "wrong" while the verdict says "right" -- i.e. does the model know more than it says?
  2. "This matches my answer" direction (Inside the Unfair Judge). Among WRONG candidates, can a probe
     tell match from differ? The difference of means gives a direction to steer with.

Reads out_probe/<judge>/hidden.npy + meta.jsonl (probe_steer.py --phase capture) and out/rows.json
(analyze.py: match / differ labels). Writes out_probe/<judge>/probes.md and directions.json (for steering).

  python3 experiments/anchoring_early_answer/probes.py --judge qwen3.5-4b
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
SINGLE = ("bbeh", "rb2math")


def qid(bench, item):
    return f"{bench}|{item.split('|')[0].rsplit('-', 1)[0] if bench == 'rb2math' else item.split('|')[0]}"


def folds_by_group(groups, k=5, seed=0):
    u = sorted(set(groups))
    rng = np.random.default_rng(seed)
    f = dict(zip(rng.permutation(u), np.arange(len(u)) % k))
    return np.array([f[g] for g in groups])


def cv_scores(X, y, groups, C=0.05):
    """Out-of-fold probability from a standardized logistic regression, folds = whole questions."""
    fold = folds_by_group(groups)
    p = np.full(len(y), np.nan)
    for f in range(fold.max() + 1):
        tr, te = fold != f, fold == f
        if len(set(y[tr])) < 2:
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd = np.where(sd < max(1e-3 * np.median(sd), 1e-8), np.inf, sd)  # drop (near-)constant dims
        z = lambda M: np.clip((M - mu) / sd, -10, 10)
        clf = LogisticRegression(C=C, max_iter=3000).fit(z(X[tr]), y[tr])
        p[te] = clf.predict_proba(z(X[te]))[:, 1]
    return p


def auc(y, s):
    ok = ~np.isnan(s)
    return roc_auc_score(y[ok], s[ok]) if len(set(y[ok])) == 2 else float("nan")


def within_auc(y, s, groups):
    """Within-question AUROC: over all (correct, wrong) candidate pairs of the SAME question, how often the
    correct one scores higher (ties count half). Question difficulty and task type cancel out."""
    by = collections.defaultdict(lambda: ([], []))
    for yi, si, g in zip(y, s, groups):
        if si == si:
            by[g][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        for a_ in pos:
            for b_ in neg:
                num += 1.0 if a_ > b_ else 0.5 if a_ == b_ else 0.0
                den += 1
    return num / den if den else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="qwen3.5-4b")
    ap.add_argument("--every", type=int, default=2, help="probe every k-th layer (all layers is slow)")
    ap.add_argument("--rows", default=str(HERE / "out" / "rows.json"), help="labels (out_llama/rows.json for Llama)")
    ap.add_argument("--dir", default="", help="folder with hidden*.npy + meta.jsonl (default out_probe/<judge>)")
    ap.add_argument("--ckpt", default="A", help="which captured position to probe: A, E (end of thinking) or C")
    a = ap.parse_args()
    d = Path(a.dir) if a.dir else HERE / "out_probe" / a.judge
    sfx = "" if a.ckpt == "A" else f"_{a.ckpt}"
    H = np.load(d / f"hidden{sfx}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / "meta.jsonl")]
    n_layers = H.shape[1]
    # E / C only exist where the judge finished thinking / wrote a verdict; missing rows are all zeros
    valid = np.array([np.any(np.asarray(H[i, -1]) != 0) for i in range(len(meta))])
    rows = {(r["judge"], r["bench"], r["item"]): r for r in json.load(open(a.rows))} if Path(a.rows).exists() else {}
    lab = [rows.get((m["judge"], m["bench"], m["item_id"])) for m in meta]
    bench = np.array([m["bench"] for m in meta])
    gold = np.array([m["gold"] for m in meta])
    margin = np.array([m["margin"] for m in meta])
    if a.ckpt != "A" and (d / "readouts.jsonl").exists():  # the judge's own verdict at the same position
        mk = {r["item_id"]: r["margin"] for r in map(json.loads, open(d / "readouts.jsonl")) if r["ckpt"] == a.ckpt}
        margin = np.array([mk.get(m["item_id"], np.nan) for m in meta])
    SUM = {"judge": a.judge, "ckpt": a.ckpt}
    groups = np.array([qid(m["bench"], m["item_id"]) for m in meta])
    layers = list(range(1, n_layers, a.every)) + ([n_layers - 1] if (n_layers - 1) % a.every != 1 % a.every else [])
    layers = sorted(set(layers))

    L = [f"# Probes at position {a.ckpt} — {a.judge}\n",
         f"{len(meta)} judgments, {n_layers - 1} layers. Hidden state = residual stream at the last token of "
         "`...VERDICT:` before the judge writes anything. Probes are logistic regressions, cross-validated with "
         "whole questions held out. AUROC 0.5 = chance, 1.0 = perfect.\n"]

    # ---------------- 1. correctness probe, with controls ----------------
    # A candidate that never wrote a final answer (cut off) is always wrong and easy to spot from surface
    # features, so the main test drops those. A text-feature baseline (prompt length, benchmark, which model
    # wrote the candidate, has-a-final-answer) shows how much is readable without the hidden state.
    sys.path.insert(0, str(HERE))
    from analyze import norm  # noqa: E402
    pool_ans = {}
    for line in open(HERE.parent / "tinker_pool" / "bbeh_results" / "answers.jsonl"):
        r = json.loads(line)
        pool_ans[(r["model"], r["item"])] = norm(r["answer"])
    has_final = np.array([(pool_ans.get((m["item_id"].split("|")[1], m["item_id"].split("|")[0])) is not None)
                          if m["bench"] == "bbeh" else True for m in meta])
    exam = [m["item_id"].split("|")[1] if m["bench"] == "bbeh" else "-" for m in meta]
    ex_names = sorted(set(exam))
    T = np.column_stack([np.log([m["n_tok"] for m in meta]), bench == "bbeh", bench == "rb2math", has_final]
                        + [np.array(exam) == e for e in ex_names]).astype(np.float32)
    spoken_all = np.array([np.nan if (r is None or r.get("spoken") is None) else r["spoken"] for r in lab], float)

    L.append("## 1. \"Is this right?\" probe vs. the judge's own verdict\n")
    L.append("Candidates that never wrote a final answer are dropped (always wrong, trivially detectable). "
             "'Text baseline' = logistic regression on prompt length, benchmark, which model wrote the candidate "
             "and whether it has a final answer -- no hidden state.\n")
    L.append("Each cell: AUROC over all candidates / **within-question** AUROC (only compares candidates of the "
             "same question, so question difficulty and task type cancel out; the fair test). 'layer-1 probe' is "
             "the same probe on the first layer, a stronger surface baseline.\n")
    L.append(f"| Set | n | verdict at {a.ckpt} | spoken verdict at C | text baseline | layer-1 probe | probe: best layer | probe |")
    L.append("|---|---|---|---|---|---|---|---|")
    sets = {"BBEH": (bench == "bbeh") & has_final & valid, "RB2 Math": (bench == "rb2math") & valid,
            "BBEH + RB2 Math": np.isin(bench, SINGLE) & has_final & valid,
            "JudgeBench (pairwise)": (bench == "judgebench") & valid}
    best, curves = {}, {}
    for name, mask in sets.items():
        idx = np.where(mask)[0]
        y = gold[idx]
        curve = {l: auc(y, cv_scores(np.asarray(H[idx, l], np.float32), y, groups[idx])) for l in layers}
        lb = max(curve, key=lambda l: curve[l] if curve[l] == curve[l] else -1)
        best[name], curves[name] = (lb, idx), curve
        g_ = groups[idx]
        two = lambda sc: f"{auc(y, sc):.3f} / **{within_auc(y, sc, g_):.3f}**"
        base = cv_scores(T[idx], y, g_, C=1.0)
        sp = spoken_all[idx] if name != "JudgeBench (pairwise)" else np.full(len(idx), np.nan)
        p1 = cv_scores(np.asarray(H[idx, 1], np.float32), y, g_)
        pb = cv_scores(np.asarray(H[idx, lb], np.float32), y, g_)
        L.append(f"| {name} | {len(idx)} | {two(margin[idx])} | {two(sp)} | {two(base)} | {two(p1)} | {lb} | {two(pb)} |")
        SUM[name] = dict(n=len(idx), verdict_within=within_auc(y, margin[idx], g_), spoken_within=within_auc(y, sp, g_),
                         probe_within=within_auc(y, pb, g_), probe_all=auc(y, pb), layer=int(lb))
    L.append("\nProbe AUROC by layer:\n")
    L.append("| Layer | " + " | ".join(curves) + " |")
    L.append("|---|" + "---|" * len(curves))
    for l in layers:
        L.append(f"| {l} | " + " | ".join(f"{curves[n][l]:.3f}" for n in curves) + " |")

    if not any(lab):  # no own answers / transcripts for this judge yet: correctness probe only
        (d / f"probes{sfx}.md").write_text("\n".join(L) + "\n\n(No own-answer labels for this judge yet; sections 2-3 skipped.)\n")
        (d / f"probe_summary{sfx}.json").write_text(json.dumps(SUM, indent=1))
        print("\n".join(L))
        return

    # ---------------- 2. does the probe see through the anchoring errors? ----------------
    lb, idx = best["BBEH + RB2 Math"]
    p = cv_scores(np.asarray(H[idx, lb], np.float32), gold[idx], groups[idx])
    sp = spoken_all[idx]
    ok = ~np.isnan(sp)
    thr = np.quantile(p[ok], 1 - sp[ok].mean())  # probe accepts as often overall as the spoken verdict does
    L.append(f"\n## 2. Wrong answers: what the judge says vs. what the layer-{lb} probe says\n")
    L.append(f"'Accepts' = says CORRECT. The probe's threshold is set so that, over all {ok.sum()} candidates, it "
             f"accepts exactly as often as the spoken verdict ({sp[ok].mean():.2f}); so any difference below is "
             "about WHICH answers it accepts, not how lenient it is.\n")
    L.append("| Candidates | n | verdict at A accepts | spoken verdict at C accepts | probe accepts |")
    L.append("|---|---|---|---|---|")
    for title, cond in (("wrong, own answer matches", lambda i: gold[i] == 0 and lab[i] and lab[i]["group"] == "match"),
                        ("wrong, own answer differs", lambda i: gold[i] == 0 and lab[i] and lab[i]["group"] == "differ"),
                        ("correct (any)", lambda i: gold[i] == 1)):
        sel = [k for k, i in enumerate(idx) if cond(i) and ok[k]]
        if sel:
            L.append(f"| {title} | {len(sel)} | {np.mean(margin[idx][sel] > 0):.2f} | {np.mean(sp[sel]):.2f} | "
                     f"{np.mean(p[sel] > thr):.2f} |")
            SUM.setdefault("same_leniency", {})[title] = dict(n=len(sel), verdict=float(np.mean(margin[idx][sel] > 0)),
                                                              spoken=float(np.mean(sp[sel])),
                                                              probe=float(np.mean(p[sel] > thr)))
    sel = [k for k, i in enumerate(idx) if gold[i] == 0 and lab[i] and lab[i]["group"] == "match" and sp[k] == 1]
    if sel:
        L.append(f"\nAnchoring errors (wrong, matches the judge's own answer, accepted in the spoken verdict): "
                 f"n = {len(sel)}; at the same leniency the probe rejects {np.mean(p[sel] <= thr):.2f} of them.")

    # ---------------- 3. agreement probe among wrong candidates ----------------
    L.append("\n## 3. \"This matches my own answer\" probe (wrong candidates only)\n")
    W = np.array([i for i in range(len(meta)) if bench[i] in SINGLE and gold[i] == 0 and lab[i] and valid[i]
                  and lab[i]["group"] in ("match", "differ")])
    yW = np.array([lab[i]["group"] == "match" for i in W], int)
    L.append(f"n = {len(W)} wrong candidates ({yW.sum()} match). Holding correctness fixed, so the probe cannot "
             "just be reading 'is this right'.\n")
    L.append(f"Text baseline (no hidden state) AUROC: {auc(yW, cv_scores(T[W], yW, groups[W], C=1.0)):.3f}. "
             f"The judge's own verdict margin at A, as a predictor of match: {auc(yW, margin[W]):.3f}.\n")
    L.append("| Layer | AUROC |")
    L.append("|---|---|")
    agree_curve = {}
    for l in layers:
        agree_curve[l] = auc(yW, cv_scores(np.asarray(H[W, l], np.float32), yW, groups[W]))
        L.append(f"| {l} | {agree_curve[l]:.3f} |")
    mid = [l for l in layers if l <= n_layers - 5]  # steering the last layers just moves the output logits
    la = max(mid, key=lambda l: agree_curve[l] if agree_curve[l] == agree_curve[l] else -1)
    lb = max(mid, key=lambda l: curves["BBEH + RB2 Math"][l] if curves["BBEH + RB2 Math"][l] == curves["BBEH + RB2 Math"][l] else -1)

    # ---------------- directions for steering ----------------
    def unit_dir(l, pos, neg):
        X = np.asarray(H[:, l], np.float32)
        v = X[pos].mean(0) - X[neg].mean(0)
        v /= np.linalg.norm(v)
        sd = float(np.std(X[np.concatenate([pos, neg])] @ v))
        return (v * sd).tolist(), sd  # scaled so alpha = 1 moves one standard deviation along v
    S = np.where(np.isin(bench, SINGLE) & valid)[0]
    corr_vec, corr_sd = unit_dir(lb, S[gold[S] == 1], S[gold[S] == 0])
    agr_vec, agr_sd = unit_dir(la, W[yW == 1], W[yW == 0])
    rng = np.random.default_rng(0)
    rv = rng.standard_normal(H.shape[2])
    rv = (rv / np.linalg.norm(rv) * corr_sd).tolist()
    # steer: all wrong single-answer candidates with a label, plus 150 correct ones as a side-effect check
    correct_ids = [meta[i]["item_id"] for i in rng.permutation(S[gold[S] == 1])[:150]]
    items = [meta[i]["item_id"] for i in W] + correct_ids
    dirs = {"correctness": dict(layer=lb, vec=corr_vec, items=items),
            "agreement": dict(layer=la, vec=agr_vec, items=items),
            "random": dict(layer=lb, vec=rv, items=items)}
    (d / f"directions{sfx}.json").write_text(json.dumps(dirs))
    L.append(f"\nSteering directions written: correctness (layer {lb}), agreement (layer {la}), random control "
             f"(layer {lb}); each scaled to one standard deviation of the projections; {len(items)} items.")
    SUM["agreement"] = dict(best=float(max(v for v in agree_curve.values() if v == v)), layer=int(la))
    (d / f"probes{sfx}.md").write_text("\n".join(L) + "\n")
    (d / f"probe_summary{sfx}.json").write_text(json.dumps(SUM, indent=1))
    print("\n".join(L))


if __name__ == "__main__":
    main()
