"""Paper numbers: every method on the same answers (paper_data.py).

Methods: verdict (forced, no reasoning), cot (judge reasons first), stretch x11 (and x4), direct (direction position),
sum (verdict + direction), cot_sum (cot + direction).
Metrics, per set, within groups (question; question x answering model for same-model sets):
  ranking   within-group AUROC x100 over right-vs-wrong pairs
  best-of-n accuracy of the top-scored answer in groups with at least one right and one wrong answer (ties split),
            next to random choice (share of right answers) and the oracle (100)
Differences vs verdict with 95% intervals from 1000 paired resamples of questions; pooled over judges by inverse
variance (judges share questions, so pooled intervals are optimistic).

  python3 experiments/beyond_capability/paper_analysis.py -> out_paper/results.json, results.md
"""
import json
from collections import defaultdict

import numpy as np

import allpairs_analyze as A
from paper_data import BIG, add_sum, pool_sets, sm_sets

OUTD = A.HERE / "out_paper"
METHODS = ["verdict", "cot", "x4", "x11", "direct", "sum", "cot_sum"]
LABEL = {"verdict": "Verdict", "cot": "Reason first", "x4": "Stretch ×4", "x11": "Stretch ×11", "direct": "Direction",
         "sum": "Verdict + direction", "cot_sum": "Reason first + direction"}


def per_group(rows, key, group):
    """{question: [auc numerator, auc denominator, best-of-n hits, best-of-n groups, share right sum]}"""
    by = defaultdict(list)
    for r in rows:
        by[group(r)].append(r)
    out = defaultdict(lambda: np.zeros(5))
    for g, rs in by.items():
        if any(r[key] is None for r in rs):
            continue
        y = np.array([r["gold"] for r in rs])
        s = np.array([r[key] for r in rs], float)
        if y.min() == y.max():
            continue
        a, b = s[y == 1][:, None], s[y == 0][None, :]
        top = s == s.max()
        out[rs[0]["qid"]] += [(a > b).sum() + 0.5 * (a == b).sum(), a.size * b.size, y[top].mean(), 1, y.mean()]
    return out


def evaluate(rows, group, n=1000):
    C = {m: per_group(rows, m, group) for m in METHODS if np.mean([r.get(m) is not None for r in rows]) > 0.9}
    # (a question with any answer missing a score drops out of every method: all methods see the same questions)
    qs = sorted(set.intersection(*[set(c) for c in C.values()]))
    if len(qs) < 5:
        return None
    M = {m: np.array([C[m][q] for q in qs]) for m in C}
    rank = lambda m, i: 100 * M[m][i, 0].sum() / M[m][i, 1].sum()  # noqa: E731
    bon = lambda m, i: 100 * M[m][i, 2].sum() / M[m][i, 3].sum()  # noqa: E731
    rng = np.random.default_rng(0)
    idx = [rng.integers(0, len(qs), len(qs)) for _ in range(n)]
    res = dict(nq=len(qs), n_answers=len(rows), random_bon=float(100 * M["verdict"][:, 4].sum() / M["verdict"][:, 3].sum()))
    for m in M:
        res[m] = dict(rank=float(rank(m, slice(None))), bon=float(bon(m, slice(None))))
        if m != "verdict":
            for met, f in (("rank", rank), ("bon", bon)):
                d = np.array([f(m, i) - f("verdict", i) for i in idx])
                res[m][f"d_{met}"] = dict(g=res[m][met] - res["verdict"][met], lo=float(np.percentile(d, 2.5)),
                                          hi=float(np.percentile(d, 97.5)))
    return res


def pooled(xs):
    xs = [x for x in xs if x and x["hi"] > x["lo"]]
    if not xs:
        return None
    w = np.array([1 / ((x["hi"] - x["lo"]) / 3.92) ** 2 for x in xs])
    g = np.array([x["g"] for x in xs])
    m, se = float((w * g).sum() / w.sum()), float(1 / np.sqrt(w.sum()))
    return dict(g=m, lo=m - 1.96 * se, hi=m + 1.96 * se, k=len(xs))


def main():
    OUTD.mkdir(exist_ok=True)
    res = {"pool": {}, "pool_unsolved": {}, "sm": {}}
    for (j, b), o in pool_sets().items():
        rows = add_sum(o["rows"], lambda r: r["qid"])
        res["pool"][f"{j}|{b}"] = dict(evaluate(rows, lambda r: r["qid"]), status=o["status"], layer=o["layer"], gap=o["gap"])
        un = [r for r in rows if r["solved"] == 0]
        res["pool_unsolved"][f"{j}|{b}"] = evaluate(un, lambda r: r["qid"])
    for (j, b, who), rows in sm_sets().items():
        rows = add_sum(rows, lambda r: (r["qid"], r["src"]))
        e = evaluate(rows, lambda r: (r["qid"], r["src"]))
        if e:
            res["sm"][f"{j}|{b}|{who}"] = e
    # pooled summaries
    summ = {}
    for name, part, keyf in (("pool", "pool", lambda k: "all"), ("pool_unsolved", "pool_unsolved", lambda k: "all"),
                             ("sm", "sm", lambda k: k.split("|")[1] + "|" + k.split("|")[2])):
        groups = defaultdict(list)
        for k, v in res[part].items():
            if v and "strict" not in k and k.split("|")[0] not in BIG:
                groups[keyf(k)].append(v)
        for g, vs in groups.items():
            summ[f"{name}|{g}"] = {m: {met: pooled([v[m][f"d_{met}"] for v in vs if m in v])
                                       for met in ("rank", "bon")} for m in METHODS if m != "verdict"}
            summ[f"{name}|{g}"]["k"] = len(vs)
            summ[f"{name}|{g}"]["verdict_rank_mean"] = float(np.mean([v["verdict"]["rank"] for v in vs]))
            summ[f"{name}|{g}"]["random_bon_mean"] = float(np.mean([v["random_bon"] for v in vs]))
            summ[f"{name}|{g}"]["verdict_bon_mean"] = float(np.mean([v["verdict"]["bon"] for v in vs]))
    res["summary"] = summ
    json.dump(res, open(OUTD / "results.json", "w"), indent=1)
    L = ["# Paper results: every method vs the forced verdict", "",
         "Gain over the forced verdict ×100 [95% interval], pooled over judges. Ranking = within-group AUROC; "
         "best-of-n = accuracy of the top-scored answer.", ""]
    for key, s in sorted(summ.items()):
        L += [f"## {key} ({s['k']} judges; verdict ranking {s['verdict_rank_mean']:.1f}, verdict best-of-n "
              f"{s['verdict_bon_mean']:.1f}, random {s['random_bon_mean']:.1f})", "",
              "| Method | Ranking gain | Best-of-n gain |", "|---|---|---|"]
        for m in METHODS[1:]:
            if s.get(m) and s[m]["rank"]:
                L.append(f"| {LABEL[m]} | {A.fmt(s[m]['rank'])} | {A.fmt(s[m]['bon'])} |")
        L.append("")
    L += ["## Per set", "", "| Set | Questions | " + " | ".join(LABEL[m] for m in METHODS) + " |",
          "|---|---|" + "---|" * len(METHODS)]
    for part in ("pool", "pool_unsolved", "sm"):
        for k, v in res[part].items():
            if not v:
                continue
            cells = [f"{v[m]['rank']:.1f}" if m in v else "–" for m in METHODS]
            L.append(f"| {part}: {k} | {v['nq']} | " + " | ".join(cells) + " |")
    (OUTD / "results.md").write_text("\n".join(L))
    print("\n".join(L[:80]))


if __name__ == "__main__":
    main()


def authorship(sets):
    """share of the within-question variance of a score explained by the answering model (between-source variance
    within a question / total within-question variance), for the direction and for the verdict."""
    out = {}
    for (j, b), o in sets.items():
        res = {}
        for key in ("direct", "verdict"):
            tot = bet = 0.0
            byq = defaultdict(list)
            for r in o["rows"]:
                byq[r["qid"]].append(r)
            for rs in byq.values():
                s = np.array([r[key] for r in rs])
                if len(s) < 2:
                    continue
                tot += ((s - s.mean()) ** 2).sum()
                bys = defaultdict(list)
                for r in rs:
                    bys[r["src"]].append(r[key])
                bet += sum(len(v) * (np.mean(v) - s.mean()) ** 2 for v in bys.values())
            res[key] = bet / tot
        out[f"{j}|{b}"] = res
    return out
