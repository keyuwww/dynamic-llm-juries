"""Majority-vote juries from existing verdicts (Nov 21 strict review, item B4). CPU only; POST HOC.

The paper's "second judge family" test is a routing/substitution experiment. This file tests explicit aggregation
policies at a matched call budget (three verdicts per item), on ALL eligible items, not selected ones:
  single            each judge alone (1 call)
  self-consistency  majority of three verdicts from ONE judge: its original verdict and two more drawn with the same
                    prompt and settings (validation/jury_repeat.py; six judges, Nemotron-3-Nano is no longer served)
  same family       majority of the three Qwen judges (3 calls)
  cross family      majority of three judges from three different families (3 calls); every such triple is evaluated
                    and the table gives the mean over triples and the three fixed triples named below
Units (one frame for all judges; see items()): RewardBench 2 Math and BFF-Bench answers, and JudgeBench pairs with the
wrong response as the candidate (approve = pick it). Eligible: every unit on which all seven judges gave a parseable
verdict, keeping wrong answers only if GLM-5.3 audits them clearly wrong (as in the paper).
Ties: three votes cannot tie; a self-consistency vote missing a repeat (no parseable verdict after two redraws) is
decided by the remaining votes, a 1-1 tie by the original verdict (counted below).
Metrics: false acceptance (wrong answers approved), false rejection (right answers rejected), balanced accuracy
(mean of the two accuracies). Stratified by the Qwens' mean belief in the answer. Paired differences resample
questions (2,000 draws). Also: how often a judge repeats an approval of a wrong answer, by its own belief.

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


def items(with_unaudited_jb=False):
    """One unit per candidate, in ONE frame for all judges.

    RewardBench 2 Math and BFF-Bench: the candidate is the graded answer; a vote is the judge's approval.
    JudgeBench: a judge's belief row targets the response that reaches ITS OWN one-sample answer (or the wrong response
    if neither does), so for the same pair one judge's "approve" can mean "picked the right response" and another's
    "picked the wrong one". Here every pair is one unit whose candidate is the WRONG response; a vote is 1 if the judge
    picks it (y if the judge's target is the wrong response, else 1 - y), and belief is each judge's belief in the
    wrong response (belief_other when its target is the right one). (The Nov 21 version mixed the two frames.)
    Pairs whose wrong response is no judge's target were never audited (all seven judges' own answers reach the right
    response); they are excluded unless with_unaudited_jb (then kept with the key's label)."""
    by, raw = collections.defaultdict(dict), {}
    for _, od, sfx in P.FAM:
        for r in json.load(open(P.HERE / od / "belief_rows_clean.json")):
            raw[r["judge"], r["item"]] = r
        for r in P.load(od, sfx):
            by[r["item"]][r["judge"]] = r
    n_all = len(by)
    keep, miss, drop, unaud = [], 0, 0, 0
    for it, v in by.items():
        if len(v) < 7:
            miss += 1
            continue
        r0 = next(iter(v.values()))
        if r0["bench"] == "judgebench":
            votes = {j: (r["y"] if r["ok"] == 0 else 1 - r["y"]) for j, r in v.items()}
            bel = {j: (r["belief"] if r["ok"] == 0 else raw[j, it].get("belief_other")) for j, r in v.items()}
            ok, aud = 0, P.GLM.get(it) == "LABEL_OK"
            if P.GLM.get(it) is None and all(r["ok"] == 1 for r in v.values()):
                unaud += 1
                if with_unaudited_jb:
                    aud = True
        else:
            votes = {j: r["y"] for j, r in v.items()}
            bel = {j: r["belief"] for j, r in v.items()}
            ok, aud = r0["ok"], r0["ok"] == 1 or r0["audited"]
        if not aud:
            drop += 1
            continue
        qb = [bel[j] for j in QWENS if bel[j] is not None]
        keep.append(dict(item=it, qid=r0["qid"], bench=r0["bench"], ok=ok, votes=votes, bel=bel,
                         qbel=float(np.mean(qb)) if qb else 0.0))
    return keep, dict(items_any_verdict=n_all, missing_some_verdict=miss, judgebench_pairs_never_audited=unaud,
                      dropped_by_audit=drop, kept=len(keep))


def decide(it, jury):
    """jury: voter keys; "judge" = its original verdict, "judge#1", "judge#2" = its repeats."""
    v = [it["votes"][j] for j in jury if it["votes"].get(j) is not None]
    if 2 * sum(v) == len(v):
        return it["votes"][jury[0]]
    return int(2 * sum(v) > len(v))


def self3(j):
    return (j, f"{j}#1", f"{j}#2")


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


def add_repeats(I):
    f = V / "jury_repeat_votes.json"
    if not f.exists():
        return [], {}
    R = json.load(open(f))
    served, short = R["judges"], collections.Counter()
    for i in I:
        for j in served:
            reps = R["votes"].get(f"{j}|{i['item']}", [])
            for k in (1, 2):
                i["votes"][f"{j}#{k}"] = reps[k - 1] if len(reps) >= k else None
            short[j] += len(reps) < 2
    return served, dict(units_with_fewer_than_two_repeats=dict(short), spent=R["spent"],
                        parser_vs_paper_original=R["parser_vs_paper_original"], cut_off=R["cut_off"])


def main():
    I, counts = items()
    served, rep_info = add_repeats(I)
    judges = sorted(FAMILY)
    cross = [t for t in itertools.combinations(judges, 3) if len({FAMILY[j] for j in t}) == 3]
    out = dict(counts=counts, repeats=rep_info, n_right=sum(i["ok"] for i in I), n_wrong=sum(1 - i["ok"] for i in I),
               n_questions=len({i["qid"] for i in I}), cross_triples=len(cross))
    pol = {f"single: {j}": (j,) for j in judges}
    pol.update({f"self-consistency: {j} x3": self3(j) for j in served})
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
        keys = ["same family: 3 Qwens"] + [f"cross family: {k}" for k in FIXED] + ["single: qwen3.6-35b-a3b"] + \
            [k for k in pol if k.startswith("self-consistency")]
        for k in keys:
            v = pol[k]
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
    for j in served:  # each judge's own three verdicts against its single verdict, and the best fixed jury against it
        e, lo, hi = boot_diff(I, self3(j), (j,))
        pd[f"{j} x3 minus {j} alone"] = dict(est=e.tolist(), lo=lo.tolist(), hi=hi.tolist())
    if served:
        sc = {k: metrics(I, v)[2] for k, v in pol.items() if k.startswith("self-consistency")}
        best = max(sc, key=sc.get)
        out["best_self_consistency"] = best
        for k, v in FIXED.items():
            e, lo, hi = boot_diff(I, v, pol[best])
            pd[f"{k} minus {best}"] = dict(est=e.tolist(), lo=lo.tolist(), hi=hi.tolist())
        e, lo, hi = boot_diff(I, tuple(QWENS), pol[best])
        pd[f"3 Qwens minus {best}"] = dict(est=e.tolist(), lo=lo.tolist(), hi=hi.tolist())
    # believed wrong answers only (Qwens' mean belief >= 4/7): paired false acceptance difference
    B = [i for i in I if i["ok"] == 0 and round(7 * i["qbel"]) >= 4]
    out["believed_wrong_false_acceptance"] = {k: float(np.mean([decide(i, v) for i in B])) for k, v in pol.items()}
    for k, v in FIXED.items():
        e, lo, hi = boot_diff(B, v, tuple(QWENS))
        pd[f"believed wrong (n={len(B)}): {k} minus 3 Qwens, false acceptance"] = [e[0], lo[0], hi[0]]
    for j in served:
        if j in QWENS:
            e, lo, hi = boot_diff(B, self3(j), tuple(QWENS))
            pd[f"believed wrong (n={len(B)}): {j} x3 minus 3 Qwens, false acceptance"] = [e[0], lo[0], hi[0]]
    out["paired"] = pd
    # reproducibility: when a judge approves a wrong answer, how often do its two repeats approve it too?
    rep = {}
    for j in served:
        for lab, lo_, hi_ in (("0/7", 0, 0), ("1-3", 1, 3), ("4-7", 4, 7)):
            A = [i for i in I if i["ok"] == 0 and i["votes"][j] == 1 and i["bel"].get(j) is not None
                 and lo_ <= round(7 * i["bel"][j]) <= hi_]
            R2 = [x for i in A for x in (i["votes"][f"{j}#1"], i["votes"][f"{j}#2"]) if x is not None]
            rep[f"{j} | own belief {lab}"] = dict(approvals=len(A), repeat_approve=float(np.mean(R2)) if R2 else None)
        for lab, lo_, hi_ in (("0/7", 0, 0), ("1-3", 1, 3), ("4-7", 4, 7)):
            W = [i for i in I if i["ok"] == 0 and i["bel"].get(j) is not None and lo_ <= round(7 * i["bel"][j]) <= hi_]
            Z = [x for i in W for x in (i["votes"][j], i["votes"][f"{j}#1"], i["votes"][f"{j}#2"]) if x is not None]
            rep[f"{j} | own belief {lab}"].update(wrong=len(W), approve_rate_all_draws=float(np.mean(Z)) if Z else None)
    pooled = {}
    for lab in ("0/7", "1-3", "4-7"):
        a = sum(rep[f"{j} | own belief {lab}"]["approvals"] for j in served)
        r = [rep[f"{j} | own belief {lab}"] for j in served if rep[f"{j} | own belief {lab}"]["repeat_approve"] is not None]
        pooled[lab] = dict(approvals=a, repeat_approve=float(sum(x["repeat_approve"] * x["approvals"] for x in r) / a)
                           if a else None)
    # pooled with intervals (questions resampled): repeat-approval after an approval, by the judge's own belief
    T = []
    for j in served:
        for i in I:
            b = i["bel"].get(j)
            if i["ok"] == 0 and i["votes"][j] == 1 and b is not None:
                k = round(7 * b)
                lab = "0/7" if k == 0 else "1-3" if k <= 3 else "4-7"
                T += [(i["qid"], lab, x) for x in (i["votes"][f"{j}#1"], i["votes"][f"{j}#2"]) if x is not None]
    byq = collections.defaultdict(list)
    for t in T:
        byq[t[0]].append(t)
    qs, rng = list(byq), np.random.default_rng(0)

    def stat(X):
        m = {lab: np.mean([x for _, l, x in X if l == lab]) for lab in ("0/7", "1-3", "4-7")}
        return np.array([m["0/7"], m["1-3"], m["4-7"], m["4-7"] - m["0/7"]])
    est = stat(T)
    Bt = np.array([stat([t for k in rng.integers(0, len(qs), len(qs)) for t in byq[qs[k]]]) for _ in range(NB)])
    lo, hi = np.nanpercentile(Bt, [2.5, 97.5], axis=0)
    pooled_ci = {n: [float(e), float(a), float(b)] for n, e, a, b in
                 zip(("0/7", "1-3", "4-7", "4-7 minus 0/7"), est, lo, hi)}
    out["repeatability"] = dict(per_judge=rep, pooled=pooled, pooled_ci=pooled_ci,
                                repeat_votes=collections.Counter(l for _, l, _ in T))
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
    if served:
        L += ["", f"Repeats: {rep_info}", "", "## Repeatability: approvals of wrong answers, by the judge's own belief\n",
              "Share of the two repeat verdicts that approve again, when the original verdict approved a wrong answer; "
              "and the approval rate over all three draws.\n"]
        for k, v in out["repeatability"]["per_judge"].items():
            ra = "–" if v["repeat_approve"] is None else p(v["repeat_approve"])
            aa = "–" if v["approve_rate_all_draws"] is None else p(v["approve_rate_all_draws"])
            L.append(f"- {k}: approvals {v['approvals']}, repeated {ra}%; wrong {v['wrong']}, approved over 3 draws {aa}%")
        L.append("- pooled (approval-weighted): " + "; ".join(
            f"{k}: {v['approvals']} approvals, repeated {p(v['repeat_approve']) if v['repeat_approve'] is not None else '–'}%"
            for k, v in out["repeatability"]["pooled"].items()))
        L.append("- pooled repeat-approval with 95% intervals (questions resampled): " + "; ".join(
            f"{k} {100 * v[0]:.1f} [{100 * v[1]:.1f}, {100 * v[2]:.1f}]" for k, v in out["repeatability"]["pooled_ci"].items()))
    (V / "jury_vote.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
