"""Rigor checks for the Nov 16 causal tests and a different-belief juror test (no new model calls).

  1. Commit first vs the usual prompt on the SAME items (paired), wrong and right answers, with 95% intervals
     (questions resampled), plus balanced accuracy (mean of right-accepted and wrong-rejected rates).
  2. Shown the answer, asked to solve: landing rate vs the rate expected from belief, per group, with intervals.
  3. "Don't re-solve" (verify) vs normal on BFF, by belief, with intervals.
  4. Different-belief juror: a Qwen judge's verdict, replaced by Nemotron-3-Super's on the items the Qwen believes
     (>= 4/7); compared with the Qwen alone and Nemotron alone, on the same items (main set, single answers + pairs).

  python3 experiments/anchoring_early_answer/rigor_checks.py   -> out/rigor_checks.md
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_verdict  # noqa: E402

QWENS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]
BINS = ["0/7", "1-3", "4-6", "7/7"]
rng = np.random.default_rng(0)


def binof(b):
    k = round(b * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def qid(r):
    return r["item"].rsplit("-", 1)[0] if r["bench"] == "rb2math" else (r.get("q") or r["item"])


def boot(pairs, f, nb=2000):
    """pairs: list of (cluster, value-tuple); f: list of value-tuples -> statistic. 95% interval over clusters."""
    by = collections.defaultdict(list)
    for c, v in pairs:
        by[c].append(v)
    keys = list(by)
    est = f([v for k in keys for v in by[k]])
    bs = []
    for _ in range(nb):
        pick = rng.integers(0, len(keys), len(keys))
        bs.append(f([v for i in pick for v in by[keys[i]]]))
    return est, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5)


def fmt(e, lo, hi, pct=True):
    s = 100 if pct else 1
    return f"{s * e:.0f}% [{s * lo:.0f}, {s * hi:.0f}]" if pct else f"{e:+.0f} [{lo:+.0f}, {hi:+.0f}]"


def main():
    rows = {(r["judge"], r["item"]): r for r in json.load(open(HERE / "out" / "belief_rows_clean.json"))}
    L = ["# Rigor checks (Nov 16)\n", "95% intervals resample whole questions (2,000 draws).\n"]

    # ---- 1. commit first, paired
    gen = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / "gen_solvefirst.jsonl"))}
    P = []  # (cluster, (gold, belief bin, usual verdict, commit verdict))
    for (j, i), r in rows.items():
        if r["bench"] not in ("rb2math", "bff") or j not in QWENS or r.get("spoken") is None:
            continue
        g = gen.get(f"solvefirst|{j}|{i}")
        v = parse_verdict(g["text"]) if g else None
        if v is None:
            continue
        P.append((qid(r), (r["target_ok"], binof(r["belief"]), int(r["spoken"] == 1), int(v))))
    L += ["## 1. Commit first vs the usual prompt (same items; three Qwens; RB2 Math + BFF)\n",
          "| answers | belief | n | usual prompt | own answer first | difference (points) |", "|---|---|---|---|---|---|"]
    for gold, name in ((0, "wrong (approved)"), (1, "right (approved)")):
        for b in BINS:
            sub = [(c, v) for c, v in P if v[0] == gold and v[1] == b]
            if len(sub) < 10:
                continue
            u = boot(sub, lambda V: np.mean([x[2] for x in V]))
            c = boot(sub, lambda V: np.mean([x[3] for x in V]))
            d = boot(sub, lambda V: 100 * (np.mean([x[3] for x in V]) - np.mean([x[2] for x in V])))
            L.append(f"| {name} | {b} | {len(sub)} | {fmt(*u)} | {fmt(*c)} | {fmt(*d, pct=False)} |")

    def bal(V, k):
        right = [x[k] for x in V if x[0] == 1]
        wrong = [x[k] for x in V if x[0] == 0]
        return (np.mean(right) + 1 - np.mean(wrong)) / 2 if right and wrong else np.nan
    bu, bc = boot(P, lambda V: bal(V, 2)), boot(P, lambda V: bal(V, 3))
    bd = boot(P, lambda V: 100 * (bal(V, 3) - bal(V, 2)))
    L += ["", f"Balanced accuracy (mean of right-approved and wrong-rejected), all {len(P)} items: usual {fmt(*bu)}, "
          f"own answer first {fmt(*bc)}, difference {fmt(*bd, pct=False)} points.\n"]

    # ---- 2. pull
    pm = {r["cache_key"]: r["verdict"] for r in map(json.loads, open(HERE / "out" / "matches_glm5.3-flash_pull.jsonl"))}
    Q = []
    for (j, i), r in rows.items():
        if r["bench"] not in ("rb2math", "bff") or j not in QWENS:
            continue
        v = pm.get(f"pull|{j}|{i}")
        if v in ("SAME", "DIFFERENT"):
            Q.append((qid(r), (r["target_ok"], binof(r["belief"]), int(v == "SAME"), r["belief"])))
    L += ["## 2. Shown the answer, asked to solve: share landing on the candidate's answer\n",
          "Expected = the average belief in the group (what landing would be with no candidate shown).\n",
          "| candidate | belief | n | lands on it | expected | difference (points) |", "|---|---|---|---|---|---|"]
    for gold, name in ((0, "wrong"), (1, "right")):
        for b in BINS:
            sub = [(c, v) for c, v in Q if v[0] == gold and v[1] == b]
            if len(sub) < 10:
                continue
            o = boot(sub, lambda V: np.mean([x[2] for x in V]))
            e = np.mean([v[3] for _, v in sub])
            d = boot(sub, lambda V: 100 * (np.mean([x[2] for x in V]) - np.mean([x[3] for x in V])))
            L.append(f"| {name} | {b} | {len(sub)} | {fmt(*o)} | {100 * e:.0f}% | {fmt(*d, pct=False)} |")

    # ---- 3. verify on BFF
    bel = {}
    for f in ("out/belief_rows_clean.json", "out_nemotron/belief_rows_clean.json"):
        for r in json.load(open(HERE / f)):
            if r["bench"] == "bff":
                bel[(r["judge"], r["item"])] = r
    V3 = collections.defaultdict(list)
    for j in QWENS + ["nemotron3-super-120b"]:
        for line in open(HERE.parent / "beyond_capability" / "out" / f"bff_judge_{j}.jsonl"):
            x = json.loads(line)
            r = bel.get((j, x["item"]))
            if x["cond"] not in ("none", "verify") or r is None or r["target_ok"] != 0:
                continue
            v = [s["verdict"] for s in x["samples"] if s.get("verdict") is not None]
            if v:
                V3[("Nemotron" if "nemotron" in j else "Qwens", x["cond"], binof(r["belief"]))].append((x["item"], (np.mean(v),)))
    L += ["", "## 3. \"Don't re-solve\" (verify) vs normal, wrong BFF answers approved\n",
          "| judges | belief | normal | verify |", "|---|---|---|---|"]
    for fam in ("Qwens", "Nemotron"):
        for b in BINS:
            a, c = V3.get((fam, "none", b), []), V3.get((fam, "verify", b), [])
            if len(a) >= 10:
                L.append(f"| {fam} | {b} (n={len(a)}) | {fmt(*boot(a, lambda V: np.mean([x[0] for x in V])))} | "
                         f"{fmt(*boot(c, lambda V: np.mean([x[0] for x in V])))} |")

    # ---- 4. different-belief juror
    nem = {r["item"]: r for r in json.load(open(HERE / "out_nemotron" / "belief_rows_clean.json"))}
    L += ["", "## 4. Different-belief juror: route a Qwen's believed items (>= 4/7) to Nemotron-3-Super\n",
          "Same items for all three columns (main set; verdicts at C). Wrong answers: share REJECTED; right answers: "
          "share APPROVED; balanced = their mean.\n",
          "| Qwen judge | items | routed | Qwen alone (balanced) | Nemotron alone | Qwen + route | wrong & believed by the Qwen: rejected (Qwen → routed) |",
          "|---|---|---|---|---|---|---|"]
    for j in QWENS:
        R = []
        for (jj, i), r in rows.items():
            n = nem.get(i)
            if jj != j or n is None or r.get("acc_C") is None or n.get("acc_C") is None or r["target_ok"] != n["target_ok"]:
                continue
            routed = r["belief"] >= 4 / 7 - 1e-9
            R.append((qid(r), (r["target_ok"], r["acc_C"], n["acc_C"], n["acc_C"] if routed else r["acc_C"], routed)))

        def balk(V, k):
            right = [x[k] for x in V if x[0] == 1]
            wrong = [1 - x[k] for x in V if x[0] == 0]
            return (np.mean(right) + np.mean(wrong)) / 2
        cells = [fmt(*boot(R, lambda V, k=k: balk(V, k))) for k in (1, 2, 3)]
        hb = [(c, v) for c, v in R if v[0] == 0 and v[4]]
        rej_q = boot(hb, lambda V: np.mean([1 - x[1] for x in V]))
        rej_r = boot(hb, lambda V: np.mean([1 - x[3] for x in V]))
        L.append(f"| {j} | {len(R)} | {sum(v[4] for _, v in R)} | " + " | ".join(cells) +
                 f" | {fmt(*rej_q)} → {fmt(*rej_r)} (n={len(hb)}) |")
    out = HERE / "out" / "rigor_checks.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
