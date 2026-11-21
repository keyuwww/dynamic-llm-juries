"""Majority-vote juries from existing verdicts (Nov 21 strict review, item B4). CPU only; no model calls; POST HOC.

The paper's "second judge family" test is a routing/substitution experiment. This file tests an explicit
aggregation policy at a matched call budget (three verdicts per item), on ALL eligible items, not selected ones:
  single          each judge alone (1 call)
  same family     majority of the three Qwen judges (3 calls)
  cross family    majority of three judges from three different families (3 calls); every such triple is evaluated
                  and the table gives the mean over triples and the two fixed triples named below
Eligible items: every original-study item (RewardBench 2 Math, JudgeBench, BFF-Bench) on which all seven judges gave a
parseable verdict, keeping wrong-labelled answers only if GLM-5.3 audits them clearly wrong (as in the paper).
Three votes, so no ties; items with any missing verdict are excluded from every policy (counted below).
Repeated verdicts from one model are not available (one verdict per judge per item), so that baseline is absent.
Metrics: false acceptance (wrong answers approved), false rejection (right answers rejected), balanced accuracy
(mean of the two accuracies). Stratified by the Qwens' mean belief in the answer. Paired differences resample
questions (2,000 draws).

  python validation/jury_vote.py   -> validation/jury_vote.{json,md}
"""
import collections
import itertools
import json
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parent
sys.path.insert(0, str(V))
import paper_numbers as P  # noqa: E402

NB = 2000
QWENS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]
FAMILY = {"qwen3.5-4b": "Qwen", "qwen3.5-9b": "Qwen", "qwen3.6-35b-a3b": "Qwen", "nemotron3-super-120b": "NVIDIA",
          "nemotron3-nano-30b": "NVIDIA", "deepseek-v4.1-flash": "DeepSeek", "kimi-k2.6": "Kimi"}
FIXED = {"Qwen3.6 + Nemotron-Super + DeepSeek": ("qwen3.6-35b-a3b", "nemotron3-super-120b", "deepseek-v4.1-flash"),
         "Qwen3.6 + Nemotron-Super + Kimi": ("qwen3.6-35b-a3b", "nemotron3-super-120b", "kimi-k2.6"),
         "Nemotron-Super + DeepSeek + Kimi (no Qwen)": ("nemotron3-super-120b", "deepseek-v4.1-flash", "kimi-k2.6")}


def items():
    by = collections.defaultdict(dict)
    for _, od, sfx in P.FAM:
        for r in P.load(od, sfx):
            by[r["item"]][r["judge"]] = r
    n_all = len(by)
    keep, miss, drop = [], 0, 0
    for it, v in by.items():
        if len(v) < 7:
            miss += 1
            continue
        r0 = next(iter(v.values()))
        if r0["ok"] == 0 and not r0["audited"]:
            drop += 1
            continue
        keep.append(dict(item=it, qid=r0["qid"], bench=r0["bench"], ok=r0["ok"], votes={j: v[j]["y"] for j in v},
                         qbel=float(np.mean([v[j]["belief"] for j in QWENS]))))
    return keep, dict(items_any_verdict=n_all, missing_some_verdict=miss, dropped_by_audit=drop, kept=len(keep))


def decide(it, jury):
    return int(sum(it["votes"][j] for j in jury) * 2 > len(jury))


def metrics(I, jury):
    W = [decide(i, jury) for i in I if i["ok"] == 0]
    Rr = [decide(i, jury) for i in I if i["ok"] == 1]
    fa = float(np.mean(W)) if W else np.nan
    fr = float(1 - np.mean(Rr)) if Rr else np.nan
    return np.array([fa, fr, 1 - (fa + fr) / 2])


def boot_diff(I, ja, jb, seed=0):
    by = collections.defaultdict(list)
    for i in I:
        by[i["qid"]].append(i)
    qs = list(by)
    rng = np.random.default_rng(seed)
    est = metrics(I, ja) - metrics(I, jb)
    d = []
    for _ in range(NB):
        S = [i for k in rng.integers(0, len(qs), len(qs)) for i in by[qs[k]]]
        d.append(metrics(S, ja) - metrics(S, jb))
    lo, hi = np.nanpercentile(np.array(d), [2.5, 97.5], axis=0)
    return est, lo, hi


def stratum(b):
    k = round(7 * b)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def main():
    I, counts = items()
    judges = sorted(FAMILY)
    cross = [t for t in itertools.combinations(judges, 3) if len({FAMILY[j] for j in t}) == 3]
    out = dict(counts=counts, n_right=sum(i["ok"] for i in I), n_wrong=sum(1 - i["ok"] for i in I),
               n_questions=len({i["qid"] for i in I}), cross_triples=len(cross))
    pol = {f"single: {j}": (j,) for j in judges}
    pol["same family: 3 Qwens"] = tuple(QWENS)
    pol.update({f"cross family: {k}": v for k, v in FIXED.items()})
    res = {k: metrics(I, v).tolist() for k, v in pol.items()}
    cm = np.array([metrics(I, t) for t in cross])
    res["cross family: mean over all triples"] = cm.mean(0).tolist()
    res["cross family: range of balanced accuracy over triples"] = [float(cm[:, 2].min()), float(cm[:, 2].max())]
    out["overall"] = res
    # strata (Qwens' mean belief): false acceptance on wrong answers, false rejection on right answers
    st = {}
    for s in P.BINS:
        S = [i for i in I if stratum(i["qbel"]) == s]
        row = dict(n_wrong=sum(1 - i["ok"] for i in S), n_right=sum(i["ok"] for i in S))
        for k, v in list(pol.items())[-4:] + [("single: qwen3.6-35b-a3b", ("qwen3.6-35b-a3b",))]:
            row[k] = metrics(S, v)[:2].tolist()
        row["cross family: mean over all triples"] = np.nanmean([metrics(S, t)[:2] for t in cross], axis=0).tolist()
        st[s] = row
    out["by_qwen_belief"] = st
    # paired differences: each fixed cross-family triple minus 3 Qwens; and minus its own Qwen alone
    pd = {}
    for k, v in FIXED.items():
        e, lo, hi = boot_diff(I, v, tuple(QWENS))
        pd[f"{k} minus 3 Qwens"] = dict(est=e.tolist(), lo=lo.tolist(), hi=hi.tolist())
        e, lo, hi = boot_diff(I, v, ("qwen3.6-35b-a3b",))
        pd[f"{k} minus Qwen3.6 alone"] = dict(est=e.tolist(), lo=lo.tolist(), hi=hi.tolist())
    e, lo, hi = boot_diff(I, tuple(QWENS), ("qwen3.6-35b-a3b",))
    pd["3 Qwens minus Qwen3.6 alone"] = dict(est=e.tolist(), lo=lo.tolist(), hi=hi.tolist())
    # believed wrong answers only (Qwens' mean belief >= 4/7): paired false acceptance difference
    B = [i for i in I if i["ok"] == 0 and round(7 * i["qbel"]) >= 4]
    out["believed_wrong_false_acceptance"] = {k: float(np.mean([decide(i, v) for i in B])) for k, v in pol.items()}
    for k, v in FIXED.items():
        e, lo, hi = boot_diff(B, v, tuple(QWENS))
        pd[f"believed wrong (n={len(B)}): {k} minus 3 Qwens, false acceptance"] = [e[0], lo[0], hi[0]]
    out["paired"] = pd
    (V / "jury_vote.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    p = lambda x: f"{100 * x:.1f}"
    L = ["# Majority-vote juries at a matched budget (Nov 21 review B4; post hoc)\n", f"Counts: {out['counts']}; "
         f"right {out['n_right']}, wrong {out['n_wrong']}, questions {out['n_questions']}; cross-family triples "
         f"{len(cross)}.\n", "| policy | false acceptance | false rejection | balanced accuracy |", "|---|---|---|---|"]
    for k, v in res.items():
        if "range" in k:
            L.append(f"| {k} | | | {p(v[0])}–{p(v[1])} |")
        else:
            L.append(f"| {k} | {p(v[0])} | {p(v[1])} | {p(v[2])} |")
    L += ["", "## By the Qwens' mean belief (false acceptance on wrong / false rejection on right, %)\n"]
    for s, row in st.items():
        L.append(f"- {s} (wrong {row['n_wrong']}, right {row['n_right']}): " + "; ".join(
            f"{k}: {p(v[0])} / {p(v[1])}" for k, v in row.items() if isinstance(v, list)))
    L += ["", "## Paired differences (points; [95%] resampling questions): false acceptance, false rejection, "
          "balanced accuracy\n"]
    for k, v in pd.items():
        if isinstance(v, dict):
            L.append(f"- {k}: " + ", ".join(f"{100 * e:+.1f} [{100 * a:+.1f}, {100 * b:+.1f}]"
                                            for e, a, b in zip(v["est"], v["lo"], v["hi"])))
        else:
            L.append(f"- {k}: {100 * v[0]:+.1f} [{100 * v[1]:+.1f}, {100 * v[2]:+.1f}]")
    L += ["", f"## False acceptance on the {len(B)} wrong answers the Qwens believe (mean >= 4/7)\n"] + [
        f"- {k}: {p(v)}" for k, v in out["believed_wrong_false_acceptance"].items()]
    (V / "jury_vote.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
