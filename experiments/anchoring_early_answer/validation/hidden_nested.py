"""Hidden-state within-question test with the layer chosen WITHOUT the test questions (Nov 21 strict review, B5).
CPU only; reads stored hidden states; POST HOC.

The paper's Table (Appendix "Hidden-State Details") picks, per model and role, the layer whose correctness direction
best separates right from wrong answers, using a cross-fit over ALL questions (beyond_capability/dir_belief_within.py;
belief is not used, but the reported statistic is computed on the same questions). Two checks remove that selection:
  nested   for each of 20 random question halvings and each half as the test half: inside the TRAINING half only,
           split its questions in two, fit the right-minus-wrong direction on one part at every layer, score the other
           (both ways), and pick the layer with the highest right-vs-wrong AUROC; fit that layer's direction on the
           whole training half and score the test half. The within-question pairwise AUROC (believed vs never-reached
           wrong answers to the same question) is computed on the assembled out-of-sample scores, averaged over splits.
  middle   a layer fixed in advance: the middle of the captured layers (no selection at all).
Also recomputed on the CURRENT audit (the BBEH audit grew on Nov 18 after the Qwen3.6-35B table was made): the
paper's own statistic (layer chosen on all questions; interval from the first split, as in dir_belief_within.py), its
top-third-of-layers average, and the model's own verdict log-odds, so the paper's table has one source.
Everything else as in dir_belief_within.py (question-centred states, difference-of-means direction, audited labels,
believed = at least half of the model's own BBEH answers reach the answer, never reached = none). Interval: question
groups resampled (1,000 draws), each draw scoring the mean over all 20 splits (so it matches the point estimate).

  python validation/hidden_nested.py   -> validation/hidden_nested.{json,md}
"""
import json
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parent
BC = V.parents[1] / "beyond_capability"
sys.path.insert(0, str(BC))
import dir_belief as db  # noqa: E402
from dir_analyze import center, dom, load  # noqa: E402
from dir_belief_robust import role_rows  # noqa: E402
from dir_belief_within import pair_auc, pairs_of  # noqa: E402

S = 20
MODELS = {"qwen3.5-9b": "main,neutral,after", "qwen3.6-35b-a3b": "roles4a,roles4b,after",
          "nemotron3-nano-30b": "roles4_s0,roles4_s1,roles4_s2,roles4_s3"}
ROLES = {"J": "snap verdict", "N": "solving", "JX": "after explanation"}


def boot_mean(scs, groups, seed=0):
    ks = list(groups)
    rng = np.random.default_rng(seed)
    v = []
    for _ in range(1000):
        kk = [ks[i] for i in rng.choice(len(ks), len(ks))]
        v.append(np.mean([pair_auc(sc, groups, kk) for sc in scs]))
    return np.nanpercentile(v, [2.5, 97.5])


def analyse(key, tags):
    parts = [load(key, t) for t in tags.split(",")]
    belief, thr = db.beliefs(key, "bbeh")
    bad = db.audited_bad("bbeh")
    rows = role_rows(key, parts, list(ROLES))
    layers = parts[0][2]
    out = {}
    for role in ROLES:
        if role not in rows:
            continue
        aids = [x for x in sorted(rows[role]) if not (rows[role][x][2]["gold"] == 0 and x in bad)]
        y = np.array([rows[role][x][2]["gold"] for x in aids])
        q = np.array([rows[role][x][2]["qid"] for x in aids])
        b = np.array([belief.get(x, np.nan) for x in aids], float)
        bel = np.where(b >= thr - 1e-9, 1, np.where(b == 0, 0, -1))
        sel = (y == 0) & ~np.isnan(b) & (bel >= 0)
        groups = pairs_of(q, bel, sel)
        nL = len(layers)
        inner = np.zeros((S, 2, nL))           # right-vs-wrong AUROC inside the training half
        test = np.zeros((S, 2, nL, len(y)))    # test-half scores at every layer
        cross = np.zeros((S, nL))              # the paper's cross-fit within-question AUROC (for the middle layer)
        rw = np.zeros((S, nL))                 # the paper's layer criterion: cross-fit right-vs-wrong AUROC, all questions
        sc0 = {}
        for li in range(nL):
            X = np.stack([rows[role][x][0][rows[role][x][1], li] for x in aids]).astype(np.float32)
            Xc = center(X, q)
            for s in range(S):
                h = db.halves(q, seed=100 + s)
                sc = np.zeros(len(y))
                for f, (tr, te) in enumerate(((h, ~h), (~h, h))):
                    d = dom(Xc[tr], y[tr])
                    sc[te] = Xc[te] @ d
                    test[s, f, li, te] = Xc[te] @ d
                    it = np.where(tr)[0]
                    g = db.halves(q[it], seed=1000 + s)  # inner split of the TRAINING questions
                    si = np.zeros(len(it))
                    for a_, b_ in ((g, ~g), (~g, g)):
                        si[b_] = Xc[it[b_]] @ dom(Xc[it[a_]], y[it[a_]])
                    inner[s, f, li] = db.auc(y[it], si)
                cross[s, li] = pair_auc(sc, groups)
                rw[s, li] = db.auc(y, sc)
                if s == 0:
                    sc0[li] = sc.copy()
        nested, chosen, scs = [], [], []
        for s in range(S):
            h = db.halves(q, seed=100 + s)
            sc = np.zeros(len(y))
            for f, te in enumerate((~h, h)):
                li = int(np.nanargmax(inner[s, f]))
                chosen.append(layers[li])
                sc[te] = test[s, f, li, te]
            nested.append(pair_auc(sc, groups))
            scs.append(sc)
        mid = nL // 2
        bl = int(np.argmax(rw.mean(0)))  # the paper's selection, recomputed on the current audit
        olo, ohi = boot_mean([sc0[bl]], groups)
        top = np.argsort(-rw.mean(0))[: max(1, nL // 3)]
        m = np.array([rows[role][x][2].get("margin") if rows[role][x][2].get("margin") is not None else np.nan
                      for x in aids], float)  # the model's own CORRECT-minus-INCORRECT log-odds at this position
        verdict = None
        if np.isfinite(m[sel]).all():
            vlo, vhi = boot_mean([m], groups)
            verdict = dict(value=float(pair_auc(m, groups)), ci=[float(vlo), float(vhi)])
        lo, hi = boot_mean(scs, groups)
        out[role] = dict(questions=len(groups), pairs=int(sum(len(v[0]) * len(v[1]) for v in groups.values())),
                         nested=float(np.mean(nested)), nested_ci=[float(lo), float(hi)],
                         chosen_layers=sorted(set(chosen)), chosen_mode=max(set(chosen), key=chosen.count),
                         middle_layer=layers[mid], middle=float(cross[:, mid].mean()),
                         paper_selection=dict(layer=layers[bl], value=float(cross[:, bl].mean()),
                                              ci_first_split=[float(olo), float(ohi)],
                                              top_third=float(cross[:, top].mean())),
                         verdict_log_odds=verdict)
        print(key, role, out[role], flush=True)
    return out


def main():
    res = {k: analyse(k, t) for k, t in MODELS.items()}
    (V / "hidden_nested.json").write_text(json.dumps(res, indent=1) + "\n")
    L = ["# Within-question hidden-state test, layer chosen without the test questions (post hoc)\n",
         "Share of (believed, never-reached) wrong-answer pairs from the same BBEH question in which the believed "
         "answer scores higher on the correctness direction (0.5 = no difference).\n",
         "| model | role | questions (pairs) | paper's selection on all questions (layer) [95%, first split] | "
         "top third of layers | nested choice [95%] | layers chosen (most often) | middle layer (layer) | "
         "verdict log-odds [95%] |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k, R in res.items():
        for role, r in R.items():
            o = r["paper_selection"]
            L.append(f"| {k} | {ROLES[role]} | {r['questions']} ({r['pairs']}) | {o['value']:.2f} ({o['layer']}) "
                     f"[{o['ci_first_split'][0]:.2f}, {o['ci_first_split'][1]:.2f}] | {o['top_third']:.2f} | {r['nested']:.2f} "
                     f"[{r['nested_ci'][0]:.2f}, {r['nested_ci'][1]:.2f}] | {r['chosen_layers']} ({r['chosen_mode']}) | "
                     f"{r['middle']:.2f} ({r['middle_layer']}) | " + ("–" if r["verdict_log_odds"] is None else
                     f"{r['verdict_log_odds']['value']:.2f} [{r['verdict_log_odds']['ci'][0]:.2f}, "
                     f"{r['verdict_log_odds']['ci'][1]:.2f}]") + " |")
    (V / "hidden_nested.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
