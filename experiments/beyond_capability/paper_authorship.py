"""Where the direction's advantage over the verdict comes from (main answer pools, small judges).

pair_split   right-vs-wrong pairs to the same question, split into same-model pairs and different-model pairs; ranking
             by verdict and direction on each, gap = direction - verdict, 95% interval from 500 question resamples;
             pooled over pairs by inverse variance.
source_pref  within question AND within correctness class: AUROC of a score for (answer by the more accurate model,
             answer by the less accurate model). 50 = the score carries no preference for the stronger model beyond
             correctness. 1000 question resamples. MMLU-Redux and MATH (BBEH has one answer per model and question).
null_share   between-model share of within-question variance for a score shuffled within question: what pure noise gets
             in this design (it replaces the earlier 'authorship share', which did not have this baseline).

  python3 experiments/beyond_capability/paper_authorship.py -> out_paper/authorship_check.json
"""
import json
from collections import defaultdict

import numpy as np

import allpairs_analyze as A
from paper_analysis import pooled
from paper_data import BIG, pool_sets

rng = np.random.default_rng(0)


def pair_split(rows, n=500):
    byq = defaultdict(list)
    for r in rows:
        byq[r["qid"]].append(r)
    per = []
    for rs in byq.values():
        c = np.zeros(6)
        for p in rs:
            if p["gold"] != 1:
                continue
            for q in rs:
                if q["gold"] != 0:
                    continue
                k = 0 if p["src"] == q["src"] else 3
                for i, key in enumerate(("verdict", "direct")):
                    c[k + i] += 1.0 if p[key] > q[key] else 0.5 if p[key] == q[key] else 0.0
                c[k + 2] += 1
        per.append(c)
    per = np.array(per)
    out = {}
    for name, k in (("same", 0), ("diff", 3)):
        if per[:, k + 2].sum() < 30:
            continue
        f = lambda P: (100 * P[:, k].sum() / P[:, k + 2].sum(), 100 * P[:, k + 1].sum() / P[:, k + 2].sum())  # noqa: E731
        v, d = f(per)
        gaps = []
        for _ in range(n):
            P = per[rng.integers(0, len(per), len(per))]
            if P[:, k + 2].sum():
                a, b = f(P)
                gaps.append(b - a)
        out[name] = dict(verdict=v, direct=d, n_pairs=int(per[:, k + 2].sum()),
                         gap=dict(g=d - v, lo=float(np.percentile(gaps, 2.5)), hi=float(np.percentile(gaps, 97.5))))
    return out


def source_pref(rows, key, n=1000):
    acc = defaultdict(list)
    for r in rows:
        acc[r["src"]].append(r["gold"])
    acc = {s: np.mean(v) for s, v in acc.items()}
    byq = defaultdict(list)
    for r in rows:
        byq[r["qid"]].append(r)
    per = []
    for rs in byq.values():
        x = np.array([r[key] for r in rs], float)
        g = np.array([r["gold"] for r in rs])
        s = np.array([r["src"] for r in rs])
        num = den = 0.0
        for t in (0, 1):
            k = g == t
            for u in set(s[k]):
                for w in set(s[k]):
                    if acc[u] > acc[w]:
                        a, b = x[k & (s == u)][:, None], x[k & (s == w)][None, :]
                        num += (a > b).sum() + 0.5 * (a == b).sum()
                        den += a.size * b.size
        per.append((num, den))
    per = np.array(per)
    pt = 100 * per[:, 0].sum() / per[:, 1].sum()
    bs = []
    for _ in range(n):
        P = per[rng.integers(0, len(per), len(per))]
        bs.append(100 * P[:, 0].sum() / P[:, 1].sum())
    return dict(g=pt, lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)))


def shares(rows):
    byq = defaultdict(list)
    for r in rows:
        byq[r["qid"]].append(r)

    def share(key, perm=False):
        tot = bet = 0.0
        for rs in byq.values():
            x = np.array([float(r[key]) for r in rs])
            s = np.array([r["src"] for r in rs])
            if len(x) < 2:
                continue
            if perm:
                x = rng.permutation(x)
            tot += ((x - x.mean()) ** 2).sum()
            bet += sum((s == u).sum() * (x[s == u].mean() - x.mean()) ** 2 for u in set(s))
        return bet / tot
    return dict(null=float(np.mean([share("verdict", True) for _ in range(20)])), gold=share("gold"),
                verdict=share("verdict"), direct=share("direct"))


def main():
    res = {"pairs": {}}
    for (j, b), o in sorted(pool_sets().items()):
        if j in BIG:
            continue
        r = dict(split=pair_split(o["rows"]))
        if b != "bbeh":
            r["src_direct"] = source_pref(o["rows"], "direct")
            r["src_verdict"] = source_pref(o["rows"], "verdict")
            r["shares"] = shares(o["rows"])
        res["pairs"][f"{j}|{b}"] = r
    P = res["pairs"]
    res["pooled"] = {f"{name}_gap": pooled([v["split"][name]["gap"] for v in P.values() if name in v["split"]])
                     for name in ("same", "diff")}
    # different-model gain on the same pairs that have same-model pairs (MMLU-Redux, MATH)
    res["pooled"]["diff_gap_matched"] = pooled([v["split"]["diff"]["gap"] for v in P.values() if "same" in v["split"]])
    json.dump(res, open(A.HERE / "out_paper" / "authorship_check.json", "w"), indent=1)
    for k, v in P.items():
        s = v["split"]
        f = lambda x: f"{x['gap']['g']:+.1f} [{x['gap']['lo']:+.1f},{x['gap']['hi']:+.1f}]" if x else "--"  # noqa: E731
        sd = v.get("src_direct")
        print(f"{k:22s} same {f(s.get('same')):22s} diff {f(s.get('diff')):22s} src_dir {sd['g'] if sd else float('nan'):.1f}")
    print(res["pooled"])


if __name__ == "__main__":
    main()
