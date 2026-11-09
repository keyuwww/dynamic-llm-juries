"""Analysis of the solve-vs-judge direction study (captures from dir_capture.py, pulled into out_dirs/<key>/).

For each model and benchmark:
  1. How well each role's hidden state separates right from wrong answers (cross-validated probe, folds = whole
     questions; within-question AUROC), per layer, and the model's spoken readout (J, S) for comparison.
  2. Are the "this is right" directions the same across roles? cosine of difference-of-means directions (with a
     split-half noise ceiling), and cross-transfer: a probe trained in one role, tested in another on held-out questions.
  3. The same on questions the model can / cannot solve.
  4. Pre-solve direction ("will I solve this?") vs the judge-mode direction.
  5. (Qwen-9B) Its own answers: does the generation-mode state know when its own answer is right?
Writes out_dirs/dirs_tables.md and out_dirs/<key>/directions_<bench>.json (for steering).

  python3 experiments/beyond_capability/dir_analyze.py --key qwen3.5-9b
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
ANC = HERE.parent / "anchoring_early_answer"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from bc_load import OUT, jl, questions, solve_stats, within_auc  # noqa: E402
from data import bbeh_correct  # noqa: E402

MODES = {"J": "judge (someone else's answer)", "G": "generate (as its own answer)", "S": "self-check (own answer + 'is it correct?')"}


def folds_by_q(qids, k=5, seed=0):
    u = sorted(set(qids))
    rng = np.random.default_rng(seed)
    f = dict(zip(rng.permutation(u), np.arange(len(u)) % k))
    return np.array([f[q] for q in qids])


def zfit(X):
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd < 1e-6, np.inf, sd)
    return mu, sd


def probe_cv(X, y, qids, C=0.05):
    fold = folds_by_q(qids)
    p = np.full(len(y), np.nan)
    for f in range(fold.max() + 1):
        tr, te = fold != f, fold == f
        if len(set(y[tr])) < 2:
            continue
        mu, sd = zfit(X[tr])
        clf = LogisticRegression(C=C, max_iter=2000).fit(np.clip((X[tr] - mu) / sd, -10, 10), y[tr])
        p[te] = clf.predict_proba(np.clip((X[te] - mu) / sd, -10, 10))[:, 1]
    return p


def transfer(Xa, ya, qa, Xb, qb, C=0.05):
    """Train on role A, score role B, never sharing a question between train and test."""
    fold_a, fold_b = folds_by_q(qa), folds_by_q(qb)  # same seed -> a question gets the same fold in both
    p = np.full(len(qb), np.nan)
    for f in range(fold_a.max() + 1):
        tr, te = fold_a != f, fold_b == f
        if len(set(ya[tr])) < 2 or not te.any():
            continue
        mu, sd = zfit(Xa[tr])
        clf = LogisticRegression(C=C, max_iter=2000).fit(np.clip((Xa[tr] - mu) / sd, -10, 10), ya[tr])
        p[te] = clf.predict_proba(np.clip((Xb[te] - mu) / sd, -10, 10))[:, 1]
    return p


def dom(X, y):
    d = X[y == 1].mean(0) - X[y == 0].mean(0)
    return d / (np.linalg.norm(d) + 1e-9)


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def center(X, q):
    """Subtract each question's mean answer state: what is left varies only between answers to the same question."""
    Xc = X.copy()
    for g in set(q):
        k = q == g
        Xc[k] -= X[k].mean(0)
    return Xc


def wq(y, s, q):
    return within_auc(y, list(s), q)[0]


def solved_labels(key):
    """(bench, qid) -> 1/0 the model solved the question; and pre-solve targets."""
    out = {}
    qs = questions()
    if key == "qwen3.5-9b":
        for q, s in solve_stats(jl(OUT / "solves_qwen3.5-9b.jsonl"), qs).items():
            out[("bbeh", q)] = s["maj_ok"]
        for r in jl(OUT / "existing_rows.jsonl"):
            if r["bench"] == "rb2math" and r["judge"] == key and r["solved"] is not None:
                out[("rb2math", r["qid"])] = r["solved"]
    else:
        for r in jl(ANC / "out_llama" / "solves.jsonl"):
            if r["bench"] == "bbeh" and str(r["clean"]) == "True":
                out[("bbeh", r["qid"])] = int(bbeh_correct(r["answer"] or "", qs[r["qid"]]["target"]))
        for r in jl(ANC / "out" / "matches_glm5.3-flash_llama3.1-8b.jsonl"):
            k = r["cache_key"].split("|")
            if "-chosen" in k[1] and r["verdict"] in ("SAME", "DIFFERENT"):
                out[("rb2math", k[1].rsplit("-", 1)[0])] = int(r["verdict"] == "SAME")
    return out


def load(key, tag):
    d = HERE / "out_dirs" / key
    H = np.load(d / f"hidden_{tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / f"meta_{tag}.jsonl")]
    layers = json.load(open(d / f"layers_{tag}.json"))["layers"]
    return H, meta, layers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="qwen3.5-9b")
    a = ap.parse_args()
    key = a.key
    H, meta, layers = load(key, "main")
    solved = solved_labels(key)
    L = [f"# Solve vs judge directions — {key}\n", f"{len(meta)} rows; layers kept: {layers}\n"]
    SUM = {}
    for bench in ("bbeh", "rb2math"):
        idx = {m: np.array([i for i, r in enumerate(meta) if r["bench"] == bench and r["mode"] == m and r["src"] != key])
               for m in ("J", "G", "S")}
        # align the three roles on the same answers
        aid = {m: [meta[i]["aid"] for i in idx[m]] for m in idx}
        common = sorted(set(aid["J"]) & set(aid["G"]) & set(aid["S"]))
        pos = {m: {a_: i for a_, i in zip(aid[m], idx[m])} for m in idx}
        rows = {m: np.array([pos[m][a_] for a_ in common]) for m in idx}
        y = np.array([meta[i]["gold"] for i in rows["J"]])
        q = np.array([meta[i]["qid"] for i in rows["J"]])
        sv = np.array([solved.get((bench, x), -1) for x in q])
        name = {"bbeh": "BBEH", "rb2math": "RB2 Math"}[bench]
        L += [f"\n## {name}: {len(common)} answers, {len(set(q))} questions ({(sv == 1).mean():.0%} of answers on questions the model solved)\n"]

        # 1. separability per role and layer
        L += ["### 1. Does each role's hidden state separate right from wrong answers? (within-question AUROC of a cross-validated probe)\n",
              "| Layer | " + " | ".join(MODES[m] for m in MODES) + " |", "|---|---|---|---|"]
        P = {m: {} for m in MODES}
        for li, l in enumerate(layers):
            if l == 0:
                continue
            cells = []
            for m in MODES:
                X = np.asarray(H[rows[m], li], np.float32)
                P[m][l] = probe_cv(X, y, q)
                cells.append(f"{wq(y, P[m][l], q):.2f}")
            L.append(f"| {l} | " + " | ".join(cells) + " |")
        best = {m: max(P[m], key=lambda l: wq(y, P[m][l], q)) for m in MODES}
        spoken = {m: np.array([meta[i]["margin"] for i in rows[m]]) for m in ("J", "S")}
        L += ["\nBest layer per role, and the model's own spoken readout (log-odds of CORRECT at the verdict position):\n",
              "| Role | best layer | probe: all questions | probe: solved | probe: **not solved** | spoken: all | spoken: solved | spoken: **not solved** |",
              "|---|---|---|---|---|---|---|---|"]
        for m in MODES:
            p = P[m][best[m]]
            c = [f"{wq(y[s], p[s], q[s]):.2f}" for s in (sv >= 0, sv == 1, sv == 0)]
            if m in spoken:
                c += [f"{wq(y[s], spoken[m][s], q[s]):.2f}" for s in (sv >= 0, sv == 1, sv == 0)]
            else:
                c += ["–"] * 3
            L.append(f"| {MODES[m]} | {best[m]} | " + " | ".join(c) + " |")
            SUM[f"{bench}|{m}"] = dict(layer=best[m], all=wq(y, p, q), solved=wq(y[sv == 1], p[sv == 1], q[sv == 1]),
                                       unsolved=wq(y[sv == 0], p[sv == 0], q[sv == 0]))

        # 2. same direction? cosine + transfer, at the judge's best layer
        lj = best["J"]
        li = layers.index(lj)
        Xm = {m: np.asarray(H[rows[m], li], np.float32) for m in MODES}
        uq = sorted(set(q))
        rng = np.random.default_rng(0)
        half = set(rng.permutation(uq)[: len(uq) // 2])
        h1 = np.array([x in half for x in q])
        Xc_ = {m: center(Xm[m], q) for m in MODES}
        D = {m: dom(Xc_[m], y) for m in MODES}
        ceil = {m: cos(dom(Xc_[m][h1], y[h1]), dom(Xc_[m][~h1], y[~h1])) for m in MODES}
        L += [f"\n### 2. Is it the same direction? (layer {lj}, the judge role's best)\n",
              "Cosine between the difference-of-means directions (right minus wrong answers), computed on question-centred "
              "states (each answer minus its question's mean) so only within-question differences count. Noise ceiling = "
              "cosine between the same role's direction from two random halves of the questions.\n",
              "| | judge | generate | self-check |", "|---|---|---|---|"]
        for m in MODES:
            L.append(f"| {MODES[m]} (ceiling {ceil[m]:.2f}) | " + " | ".join(f"{cos(D[m], D[n]):.2f}" for n in MODES) + " |")
        # random baseline cosine for d dims
        L.append(f"\n(Two random directions in {Xm['J'].shape[1]} dimensions: cosine ≈ ±{1 / np.sqrt(Xm['J'].shape[1]):.3f}.)\n")
        L += ["Cross-transfer: a probe trained in one role (rows), tested in another (columns), on held-out questions. "
              "Within-question AUROC, all / **not solved**.\n",
              "| trained on \\ tested on | judge | generate | self-check |", "|---|---|---|---|"]
        for m in MODES:
            cells = []
            for n in MODES:
                p = transfer(Xm[m], y, q, Xm[n], q)
                cells.append(f"{wq(y, p, q):.2f} / **{wq(y[sv == 0], p[sv == 0], q[sv == 0]):.2f}**")
                SUM[f"{bench}|transfer|{m}->{n}"] = dict(all=wq(y, p, q), unsolved=wq(y[sv == 0], p[sv == 0], q[sv == 0]))
            L.append(f"| {MODES[m]} | " + " | ".join(cells) + " |")
        SUM[f"{bench}|cos"] = {f"{m}{n}": cos(D[m], D[n]) for m in MODES for n in MODES}
        SUM[f"{bench}|ceil"] = ceil

        # cosine at every layer (direction from each role at that layer), with split-half ceilings
        L += ["\nCosine judge-vs-generate and judge-vs-self-check at every layer, question-centred (ceilings: judge / generate split-half):\n",
              "| Layer | judge·generate | judge·self-check | ceiling judge | ceiling generate |", "|---|---|---|---|---|"]
        for li2, l in enumerate(layers):
            if l == 0:
                continue
            Xl = {m: center(np.asarray(H[rows[m], li2], np.float32), q) for m in MODES}
            Dl = {m: dom(Xl[m], y) for m in MODES}
            cj = cos(dom(Xl["J"][h1], y[h1]), dom(Xl["J"][~h1], y[~h1]))
            cg = cos(dom(Xl["G"][h1], y[h1]), dom(Xl["G"][~h1], y[~h1]))
            L.append(f"| {l} | {cos(Dl['J'], Dl['G']):.2f} | {cos(Dl['J'], Dl['S']):.2f} | {cj:.2f} | {cg:.2f} |")
            SUM.setdefault(f"{bench}|cos_by_layer", {})[l] = dict(JG=cos(Dl["J"], Dl["G"]), JS=cos(Dl["J"], Dl["S"]), cj=cj, cg=cg)

        # 4. pre-solve direction
        pidx = [i for i, r in enumerate(meta) if r["bench"] == bench and r["mode"] == "P" and (bench, r["qid"]) in solved]
        if pidx:
            yp = np.array([solved[(bench, meta[i]["qid"])] for i in pidx])
            Xp = np.asarray(H[pidx, li], np.float32)
            if len(set(yp)) == 2:
                pp = probe_cv(Xp, yp, [meta[i]["qid"] for i in pidx])
                dp = dom(Xp, yp)
                # judge-mode "is this question hard" direction: questions the model solves vs not, judge rows
                dj_solved = dom(Xm["J"][sv >= 0], (sv[sv >= 0] == 1).astype(int))
                L += [f"\n### 4. 'Will I solve this?' before answering (layer {lj})\n",
                      f"Probe AUROC (questions held out): **{roc_auc_score(yp, pp):.2f}** over {len(pidx)} questions "
                      f"({yp.mean():.0%} solved).\n\n"
                      f"Cosines: pre-solve 'will I solve it' vs judge 'is this answer right': {cos(dp, D['J']):.2f}; "
                      f"judge 'is this answer right' vs judge 'is this a question I solve' (judge rows, solved minus not solved): "
                      f"{cos(dj_solved, D['J']):.2f}; pre-solve vs that judge-role solved direction: {cos(dp, dj_solved):.2f}.\n"]
                SUM[f"{bench}|presolve"] = dict(auc=roc_auc_score(yp, pp), cos_J=cos(dp, D["J"]), cos_Jsolved=cos(dj_solved, D["J"]))

        # directions for steering: computed on one half of the questions, applied to the other half
        dirs = {}
        for hname, mask in (("h1", h1), ("h2", ~h1)):
            for m in ("J", "G"):
                v = dom(Xm[m][mask], y[mask])
                dirs[f"{m}_{hname}"] = dict(layer=lj, vec=v.tolist(), mu=float((Xm["J"][mask] @ v).mean()),
                                            sd=float((Xm["J"][mask] @ v).std()))
            r_ = rng.normal(size=Xm["J"].shape[1])
            r_ /= np.linalg.norm(r_)
            dirs[f"R_{hname}"] = dict(layer=lj, vec=r_.tolist(), mu=float((Xm["J"][mask] @ r_).mean()),
                                      sd=float((Xm["J"][mask] @ r_).std()))
        json.dump(dict(dirs=dirs, h1=sorted(half)), open(HERE / "out_dirs" / key / f"directions_{bench}.json", "w"))

    # 5. own answers (Qwen-9B)
    own_p = HERE / "out_dirs" / key / "hidden_own.npy"
    if own_p.exists():
        Ho, mo, lo = load(key, "own")
        L += ["\n## Its own answers (BBEH, 5 thinking-off answers per question)\n",
              "Does the model's state after writing its OWN answer know whether that answer is right? Within-question "
              "AUROC compares its right and wrong answers to the same question.\n",
              "| Role | best layer | probe | spoken (self-check) | judge-role probe transferred here |", "|---|---|---|---|---|"]
        # judge-role probe on pool candidates, applied to own answers
        jrows = np.array([i for i, r in enumerate(meta) if r["bench"] == "bbeh" and r["mode"] == "J" and r["src"] != key])
        yj = np.array([meta[i]["gold"] for i in jrows])
        for m in ("G", "S"):
            ro = np.array([i for i, r in enumerate(mo) if r["mode"] == m])
            yo = np.array([mo[i]["gold"] for i in ro])
            qo = np.array([mo[i]["qid"] for i in ro])
            res = {}
            for li_, l in enumerate(lo):
                if l == 0:
                    continue
                res[l] = probe_cv(np.asarray(Ho[ro, li_], np.float32), yo, qo)
            bl = max(res, key=lambda l: wq(yo, res[l], qo))
            sp = np.array([mo[i]["margin"] for i in ro]) if m == "S" else None
            li_j = layers.index(SUM["bbeh|J"]["layer"])
            Xj = np.asarray(H[jrows, li_j], np.float32)
            mu, sd = zfit(Xj)
            clf = LogisticRegression(C=0.05, max_iter=2000).fit(np.clip((Xj - mu) / sd, -10, 10), yj)
            pt = clf.predict_proba(np.clip((np.asarray(Ho[ro, lo.index(SUM['bbeh|J']['layer'])], np.float32) - mu) / sd, -10, 10))[:, 1]
            L.append(f"| {MODES[m]} | {bl} | {wq(yo, res[bl], qo):.2f} | {wq(yo, sp, qo) if sp is not None else float('nan'):.2f} | {wq(yo, pt, qo):.2f} |")
            SUM[f"own|{m}"] = dict(probe=wq(yo, res[bl], qo), transfer_from_J=wq(yo, pt, qo))
        L.append(f"\n({len(set(qo))} questions; pairs only exist where the model's 5 answers include both right and wrong ones.)\n")

    (HERE / "out_dirs" / f"dirs_tables_{key}.md").write_text("\n".join(L) + "\n")
    json.dump(SUM, open(HERE / "out_dirs" / f"dirs_summary_{key}.json", "w"), indent=1, default=float)
    print("\n".join(L))


if __name__ == "__main__":
    main()
