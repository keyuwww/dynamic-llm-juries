#!/usr/bin/env python
"""Zero-label belief rule on JudgeBench and RB2 Safety with our own belief runs (belief_solve.py). Cheap judges Qwen3.5-4B / 9B, their normal verdicts.
  JudgeBench  disagree = the judge's own answer matches exactly one response (A or B) and its verdict picked the other one
  Safety      disagree = it called the response appropriate while the response's behaviour (comply/refuse) differs from what the judge itself would do,
              or called it inappropriate while the behaviour matches
Zero-label rule: escalate disagreements first, then random. Baselines: verdict-token probability (confidence), verdict-only rule (Safety: items called
appropriate first; JudgeBench: random), 10 reruns (share of samples agreeing with the greedy verdict), random; README probe (confirm_probe.py) for reference.
Accuracy with 20% escalated (unfinished answers first) to the README's stronger judge. 95% paired bootstrap CIs over questions.
Pre-registered: the zero-label rule beats BOTH confidence and the verdict-only rule with CIs above 0 in at least 2 of the 4 settings."""
import json, sys, numpy as np, pandas as pd
S = sys.argv[1]; TG = json.load(open("targets/strong_judge_correct.json")); PROBE = {("Qwen3.5-4B", "judgebench"): 77.2, ("Qwen3.5-9B", "judgebench"): 79.2, ("Qwen3.5-4B", "rb2safety"): 87.7, ("Qwen3.5-9B", "rb2safety"): 89.0}
def esc(trust, ol, oh, fin, tie, rate=0.2):
    n = len(ol); m = int(round(rate * n)); k = np.lexsort((tie, np.where(~fin, -1e9, trust))); e = np.zeros(n, bool); e[k[:m]] = True; return np.where(e, oh, ol).mean()
def boot(f, g, nb=1000):
    gi = {q: np.where(g == q)[0] for q in np.unique(g)}; ug = np.array(list(gi)); rb = np.random.default_rng(7)
    D = np.array([f(np.concatenate([gi[q] for q in rb.choice(ug, len(ug))])) for _ in range(nb)]) * 100; return np.percentile(D, 2.5), np.percentile(D, 97.5)
rows, passes = [], 0
for J in ["Qwen3.5-4B", "Qwen3.5-9B"]:
    B = [json.loads(l) for l in open(f"{S}/beliefsolve_{J}/{J}__beliefsolve.jsonl")]; by = lambda k: {r["key"]: r for r in B if r["kind"] == k}
    for b in ["judgebench", "rb2safety"]:
        base = f"local_results/{J}__{b}__uncertainty__n1_t0.0/{J}__{b}__uncertainty__n1_t0.0"; L = pd.read_json(f"{base}_gen.jsonl", lines=True, dtype={"item_id": str})
        it = pd.read_csv(f"{base}_items.csv", dtype={"item_id": str}).set_index("item_id"); L = L.set_index("item_id").loc[it.index]; ids = list(it.index)
        ol = L.correct.values.astype(int); fin = L.verdict.notna().values; oh = np.array([TG[J][b][i] for i in ids]); g = it.group.astype(str).values; n = len(ol)
        T = pd.read_csv(f"{base}_tokstats.csv", dtype={"item_id": str}).set_index("item_id").reindex(ids); conf = np.nan_to_num(T.verdict_prob.values, nan=0.0)
        Sm = pd.read_json(f"local_results/{J}__{b}__uncertainty__n10_t0.7/{J}__{b}__uncertainty__n10_t0.7_gen.jsonl", lines=True, dtype={"item_id": str})
        cons = np.array([((Sm[Sm.item_id == i].verdict == L.loc[i, "verdict"]).mean() if fin[k] else 0.0) for k, i in enumerate(ids)])
        if b == "judgebench":
            M = by("jb_match"); pick = np.array([M[i]["parsed"] if i in M else None for i in ids], dtype=object); v = L.verdict.astype(str).values
            dis = np.array([p in ("A", "B") and p != vv for p, vv in zip(pick, v)]); informative = np.isin(pick, ["A", "B"]); vo_key = np.zeros(n)
        else:
            Pol = by("sf_policy"); Beh = by("sf_behavior"); Itm = by("sf_item"); pol = np.array([Pol.get(Itm[i]["parsed"], {}).get("parsed") for i in ids], dtype=object)
            beh = np.array([Beh.get(i, {}).get("parsed") for i in ids], dtype=object); ok = np.array([p is not None and q is not None for p, q in zip(pol, beh)])
            match = ok & (pol == beh); v = (L.verdict.values == 1.0); dis = ok & ((v & ~match) | (~v & match)); informative = ok; vo_key = np.where(v, 0, 1)
        tie = np.random.default_rng(12345).random(n)
        f = {"zero_label_belief": lambda bi: np.mean([esc((~dis).astype(float)[bi] + 0.5 * np.random.default_rng(s).random(n)[bi], ol[bi], oh[bi], fin[bi], tie[bi]) for s in range(20)]),
             "confidence": lambda bi: esc(conf[bi], ol[bi], oh[bi], fin[bi], tie[bi]),
             "verdict_only": lambda bi: np.mean([esc((vo_key + 0.5 * np.random.default_rng(s).random(n))[bi], ol[bi], oh[bi], fin[bi], tie[bi]) for s in range(20)]),
             "reruns10": lambda bi: esc(cons[bi], ol[bi], oh[bi], fin[bi], tie[bi])}
        al = np.arange(n); row = dict(judge=J, bench=b, random=(ol.mean() + 0.2 * (oh.mean() - ol.mean())) * 100, **{k: fn(al) * 100 for k, fn in f.items()}, probe_README=PROBE[(J, b)],
                                      informative=informative.mean() * 100, disagree=dis.mean() * 100, cheap_wrong_when_disagree=(1 - ol[dis]).mean() * 100 if dis.any() else np.nan)
        l1, h1 = boot(lambda bi: f["zero_label_belief"](bi) - f["confidence"](bi), g); l2, h2 = boot(lambda bi: f["zero_label_belief"](bi) - f["verdict_only"](bi), g)
        row["minus_conf"] = f"{row['zero_label_belief'] - row['confidence']:+.1f} [{l1:+.1f},{h1:+.1f}]"; row["minus_verdict"] = f"{row['zero_label_belief'] - row['verdict_only']:+.1f} [{l2:+.1f},{h2:+.1f}]"
        passes += (l1 > 0) and (l2 > 0); rows.append(row)
pd.set_option("display.width", 280); print(pd.DataFrame(rows).round(1).to_string(index=False))
print(f"\nPRE-REGISTERED (beats confidence AND verdict-only with CIs above 0 in >= 2 of 4): {passes} -> {'PASS' if passes >= 2 else 'FAIL'}")
