"""Where the direction's advantage over the verdict comes from (main answer pools, small judges).

pair_split   right-vs-wrong pairs to the same question, split into same-model pairs and different-model pairs; ranking
             by verdict and direction on each, gap = direction - verdict, 95% interval from 500 question resamples;
             pooled: equal-weight mean over pairs, synchronised question bootstrap (sync_stats.py).
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
import sync_stats as S
from paper_analysis import pooled
from paper_data import BIG, pool_sets

rng = np.random.default_rng(0)


def pair_split(rows, n=500, arrays=False):
    byq = defaultdict(list)
    for r in rows:
        byq[r["qid"]].append(r)
    per, qids = [], []
    for qid, rs in byq.items():
        qids.append(qid)
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
    if arrays:
        return qids, per
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


def controls(pool_keys):
    """authorship_controls_modal.py output, pooled over the main-pool pairs (MMLU-Redux, MATH) with the synchronised
    bootstrap: gains of c, c_perp (authorship plane removed), c_gb (generator-balanced fit) over the verdict on all /
    same-model / different-model pairs; removal share; permutation and isotropic nulls; generator holdout."""
    f = A.HERE / "out_paper" / "authorship_controls.json"
    if not f.exists():
        return None
    Cx = json.load(open(f))
    keys = [k for k in Cx if k in pool_keys]
    arr = {}
    for k in keys:
        j, b = k.split("|")
        P = Cx[k]["perq"]
        qs = sorted(set.intersection(*[set(P[m]) for m in P]))
        arr[(j, b)] = {m: (qs, np.array([P[m][x] for x in qs])) for m in P}
    stats = {}
    for part, col in (("all", (0, 1)), ("same", (2, 3)), ("diff", (4, 5))):
        stats |= {f"{m}|{part}": S.auc_gain(m, col=col) for m in ("c", "c_perp", "c_gb")}
        stats |= {f"{m}|level|{part}": S.level(m, col=col) for m in ("verdict", "c", "c_perp", "c_gb")}
    out = {}
    for b in ("mmlu", "math", "both"):
        sub = {p: v for p, v in arr.items() if b == "both" or p[1] == b}
        est, draws = S.boot(sub, stats)
        for part in ("all", "same", "diff"):
            with np.errstate(divide="ignore", invalid="ignore"):
                r = (draws[f"c|{part}"] - draws[f"c_perp|{part}"]) / draws[f"c|{part}"]
            r = r[np.isfinite(r)]
            g0 = (est[f"c|{part}"]["g"] - est[f"c_perp|{part}"]["g"]) / est[f"c|{part}"]["g"]
            est[f"removed|{part}"] = dict(g=g0, lo=float(np.percentile(r, 2.5)), hi=float(np.percentile(r, 97.5)))
        est["n_pairs"] = len(sub)
        out[b] = est
    # nulls, per pair: removal of the observed plane vs 100 label-permuted planes and 100 isotropic planes (all pairs)
    per = {}
    for k in keys:
        P, x = Cx[k]["perq"], Cx[k]
        auc = lambda d: 100 * sum(v[0] for v in d.values()) / sum(v[1] for v in d.values())  # noqa: E731
        c, cp, v = auc(P["c"]), auc(P["c_perp"]), auc(P["verdict"])
        perm = np.array([a[0] for a in x["perm_auc"]])
        iso = np.array([a[0] for a in x["iso_auc"]])
        per[k] = dict(layer=x["layer"], c=c, c_perp=c_perp if (c_perp := cp) else cp, verdict=v, c_gb=auc(P["c_gb"]),
                      removed=c - cp, perm_removed_mean=float(c - perm.mean()), perm_removed_max=float(c - perm.min()),
                      perm_p=float((np.sum(c - perm >= c - cp) + 1) / (len(perm) + 1)),
                      iso_removed_max=float(c - iso.min()))
    # generator holdout: same-model pairs of the held-out model, c fitted without it vs with it, and the verdict
    hold = {}
    for G in ("qwen3.5-4b", "nemotron3-super-120b", "qwen3.6-35b-a3b"):
        harr = {}
        for k in keys:
            j, b = k.split("|")
            H = Cx[k]["holdout"][G]
            qs = sorted(set.intersection(*[set(H[m]) for m in H]))
            if qs:
                harr[(j, b)] = {m: (qs, np.array([H[m][x] for x in qs])) for m in H}
        st = {f"{m}|gain": S.auc_gain(m) for m in ("c_ho", "c_all")} | {"verdict|level": S.level("verdict")}
        st["ho_minus_all"] = lambda T: S.auc_gain("c_ho")(T) - S.auc_gain("c_all")(T)
        hold[G], _ = S.boot(harr, st)
    return dict(pooled=out, per_pair=per, holdout=hold)


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
    # primary: equal-weight mean over pairs, synchronised question bootstrap (sync_stats.py)
    arr = {}
    for (j, b), o in sorted(pool_sets().items()):
        if j in BIG:
            continue
        qids, per = pair_split(o["rows"], arrays=True)
        arr[(j, b)] = {"x": (qids, per)}
    gap = lambda k: lambda T: 100 * (T["x"][k + 1] - T["x"][k]) / T["x"][k + 2] if T["x"][k + 2] >= 30 else None  # noqa: E731
    lvl = lambda k, i: lambda T: 100 * T["x"][k + i] / T["x"][k + 2] if T["x"][k + 2] >= 30 else None  # noqa: E731
    stats = {"same_gap": gap(0), "diff_gap": gap(3), "same_verdict": lvl(0, 0), "same_direct": lvl(0, 1),
             "diff_verdict": lvl(3, 0), "diff_direct": lvl(3, 1)}
    est, draws = S.boot(arr, stats)
    has_same = {p for p in arr if "same" in P[f"{p[0]}|{p[1]}"]["split"]}
    est_m, _ = S.boot({p: v for p, v in arr.items() if p in has_same}, {"diff_gap_matched": gap(3), "same_gap": gap(0)})
    res["pooled"] = dict(est, diff_gap_matched=est_m["diff_gap_matched"], same_gap_matched=est_m["same_gap"])
    # legacy (secondary): inverse-variance pooling of per-pair intervals
    res["pooled_legacy_invvar"] = {f"{name}_gap": pooled([v["split"][name]["gap"] for v in P.values() if name in v["split"]])
                                   for name in ("same", "diff")}
    res["pooled_legacy_invvar"]["diff_gap_matched"] = pooled([v["split"]["diff"]["gap"] for v in P.values() if "same" in v["split"]])
    res["controls"] = controls({f"{j}|{b}" for (j, b) in pool_sets() if j not in BIG})
    json.dump(res, open(A.HERE / "out_paper" / "authorship_check.json", "w"), indent=1)
    for k, v in P.items():
        s = v["split"]
        f = lambda x: f"{x['gap']['g']:+.1f} [{x['gap']['lo']:+.1f},{x['gap']['hi']:+.1f}]" if x else "--"  # noqa: E731
        sd = v.get("src_direct")
        print(f"{k:22s} same {f(s.get('same')):22s} diff {f(s.get('diff')):22s} src_dir {sd['g'] if sd else float('nan'):.1f}")
    print(res["pooled"])


if __name__ == "__main__":
    main()
