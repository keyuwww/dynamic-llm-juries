#!/usr/bin/env python3
"""
When do LLM judges (and answer models) agree, and are they wrong together? Checks three claims from the
literature in Keyu's review against our stored outputs, with no new API calls:

  1. Kim et al. 2025: when two models are both wrong, they give the same wrong answer ~60% of the time.
     Testable only where wrong answers can differ: BBEH answer models (free-form answers). For yes/no or A/B
     judge verdicts there is only one wrong verdict, so two wrong judges always "agree"; there we measure how
     much one judge's error raises the chance another errs (lift) instead.
  2. Kohli 2026: nine frontier judges carry ~2.2 independent votes. We compute the effective number of
     independent judges from the error correlations.
  3. Goel et al. 2025 (CAPA): errors correlate more between more capable models.

Then agreement patterns: how the 8 votes split and how accurate the majority is at each split, how often a
unanimous verdict is wrong (and in which direction), agreement within vs across model families, and which
judges are right when they dissent alone.

  uv run python experiments/cross_benchmark/agreement_patterns.py
Writes results/agreement_patterns.json.
"""
import json
import re
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TP = HERE.parent / "tinker_pool"
JUDGES = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
          "nemotron3-super-120b", "nemotron3-nano-30b"]
FAMILY = {"gpt-oss-120b": "gpt-oss", "gpt-oss-20b": "gpt-oss", "deepseek-v3.1": "deepseek", "qwen3.6-35b-a3b": "qwen",
          "qwen3.5-9b": "qwen", "qwen3.5-4b": "qwen", "nemotron3-super-120b": "nemotron", "nemotron3-nano-30b": "nemotron"}
SOURCES = {  # benchmarks whose full 8-judge verdicts are on disk
    "bff": TP / "bff_results_max4096/judgments.jsonl",
    "mtb": TP / "mtb_results_max4096/judgments.jsonl",
    "bffpair": TP / "bffpair_results_max4096/judgments.jsonl",
}


def spearman(a, b):
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


# ----------------------------------------------------------------------------- 1. same wrong answer (BBEH)
def normalize(ans):
    a = str(ans or "")
    for p in ["The answer is:", "The final answer is ", "The final answer is: ", "The answer is "]:
        if p in a:
            a = a.split(p)[-1].strip()
    a = a.strip().split("\n")[0].lower().replace(", ", ",").replace("**", "").replace("$", "").strip()
    a = re.sub(r"\\boxed\{(.*)\}", r"\1", a).rstrip(".").strip()
    return a


def same_wrong_answer(path, n_shuffle=200, seed=0):
    rows = [json.loads(l) for l in open(path)]
    d = pd.DataFrame([dict(item=r["item"], task=r["task"], model=r["model"], pred=normalize(r.get("answer")),
                           correct=int(r.get("correct") or 0)) for r in rows])
    d = d[d.pred.str.len() > 0]
    P = d.pivot_table(index="item", columns="model", values="pred", aggfunc="first")
    C = d.pivot_table(index="item", columns="model", values="correct", aggfunc="first")
    task = d.drop_duplicates("item").set_index("item").task
    models = [m for m in P.columns]
    same, n = 0, 0
    by_task = {}
    pairs_wrong = []  # (task, item, pred_a, pred_b)
    for a, b in combinations(models, 2):
        m = (C[a] == 0) & (C[b] == 0) & P[a].notna() & P[b].notna()
        for it in P.index[m]:
            s = P.at[it, a] == P.at[it, b]
            same += s
            n += 1
            t = task[it]
            by_task.setdefault(t, [0, 0])
            by_task[t][0] += s
            by_task[t][1] += 1
            pairs_wrong.append((t, it, a, b))
    # chance: model a's wrong answer on item i vs model b's wrong answer on another item of the same task
    rng = np.random.default_rng(seed)
    wrong_preds = {}
    for it in P.index:
        for mdl in models:
            if C.at[it, mdl] == 0 and isinstance(P.at[it, mdl], str):
                wrong_preds.setdefault(task[it], []).append((it, P.at[it, mdl]))
    hits, tot = 0, 0
    for _ in range(n_shuffle):
        for t, it, a, b in pairs_wrong:
            pool = [p for (j, p) in wrong_preds[t] if j != it]
            if not pool:
                continue
            hits += P.at[it, a] == pool[rng.integers(len(pool))]
            tot += 1
    both_right = sum(((C[a] == 1) & (C[b] == 1)).sum() for a, b in combinations(models, 2))
    return dict(n_questions=int(P.shape[0]), n_models=len(models), both_wrong_pairs=n,
                same_wrong=float(same / max(n, 1)), chance_same=float(hits / max(tot, 1)), both_right_pairs=int(both_right),
                by_task={t: dict(n=v[1], same=float(v[0] / v[1])) for t, v in sorted(by_task.items()) if v[1] >= 10})


# ----------------------------------------------------------------------------- 2-3. judges
def load(bench, cond="none"):
    rows = []
    for l in open(SOURCES[bench]):
        r = json.loads(l)
        if r["condition"] != cond or r["judge"] not in JUDGES:
            continue
        key = r["item_id"] if bench == "bffpair" else f"{r['item_id']}|{r.get('examinee')}"
        v = int((r.get("vote_share") or 0) > 0.5)
        rows.append(dict(key=key, judge=r["judge"], verdict=v, gold=int(r["gold"])))
    d = pd.DataFrame(rows).drop_duplicates(["key", "judge"], keep="last")
    V = d.pivot_table(index="key", columns="judge", values="verdict").dropna()[JUDGES].astype(int)
    gold = d.drop_duplicates("key").set_index("key").gold.loc[V.index].values
    return V, gold


def judge_patterns(V, gold):
    Vm = V.values
    A = (Vm == gold[:, None]).astype(int)
    E = 1 - A
    J = len(JUDGES)
    acc = A.mean(0)
    # co-error lift
    lifts, phis, pair_acc = [], [], []
    for i, j in combinations(range(J), 2):
        pa, pb = E[:, i].mean(), E[:, j].mean()
        both = (E[:, i] & E[:, j]).mean()
        lifts.append(both / max(pa, 1e-9) / max(pb, 1e-9))
        phis.append(float(np.corrcoef(E[:, i], E[:, j])[0, 1]))
        pair_acc.append((acc[i] + acc[j]) / 2)
    cond = []
    for i in range(J):
        for j in range(J):
            if i != j and E[:, i].sum():
                cond.append(dict(a=JUDGES[i], b=JUDGES[j], p_b_wrong=float(E[:, j].mean()),
                                 p_b_wrong_given_a=float(E[E[:, i] == 1, j].mean())))
    rho = float(np.mean(phis))
    keep = E.std(0) > 0  # a judge with no errors has no error correlation
    corr = np.nan_to_num(np.corrcoef(E[:, keep].T))
    ev = np.clip(np.linalg.eigvalsh(corr), 0, None)
    phis = [p if np.isfinite(p) else 0.0 for p in phis]
    rho = float(np.mean(phis))
    # vote splits
    k = Vm.sum(1)  # judges saying "correct" / "first is better"
    maj = (k > J / 2).astype(int)
    splits = {}
    for s in range(J + 1):
        m = k == s
        if m.any():
            splits[f"{s}-{J - s}"] = dict(n=int(m.sum()), share=float(m.mean()),
                                         majority_right=float((maj[m] == gold[m]).mean()) if s != J / 2 else None,
                                         gold_positive=float(gold[m].mean()))
    unan = (k == 0) | (k == J)
    unan_wrong = unan & (Vm[:, 0] != gold)
    # families
    within, across = [], []
    for i, j in combinations(range(J), 2):
        agree = float((Vm[:, i] == Vm[:, j]).mean())
        (within if FAMILY[JUDGES[i]] == FAMILY[JUDGES[j]] else across).append(
            dict(pair=f"{JUDGES[i]} + {JUDGES[j]}", agree=agree, phi=phis[list(combinations(range(J), 2)).index((i, j))]))
    # lone dissenters
    lone = {}
    for s, side in [(1, 1), (J - 1, 0)]:  # exactly one judge says positive / exactly one says negative
        m = np.where(k == s)[0]
        for r in m:
            jj = int(np.where(Vm[r] == side)[0][0])
            lone.setdefault(JUDGES[jj], [0, 0])
            lone[JUDGES[jj]][0] += int(Vm[r, jj] == gold[r])
            lone[JUDGES[jj]][1] += 1
    minority_right = float(((maj != gold) & (A.sum(1) > 0)).mean())
    return dict(
        n=int(len(gold)), acc={j: float(a) for j, a in zip(JUDGES, acc)},
        co_error=dict(mean_lift=float(np.mean(lifts)), mean_phi=rho,
                      mean_p_wrong=float(E.mean()),
                      mean_p_wrong_given_other_wrong=float(np.mean([c["p_b_wrong_given_a"] for c in cond])),
                      both_wrong_agree="100% by construction (one wrong verdict per item)"),
        effective_votes=dict(n_judges=J, kish=float(J / (1 + (J - 1) * rho)), participation_ratio=float(ev.sum() ** 2 / (ev ** 2).sum())),
        capability=dict(spearman_pair_accuracy_vs_phi=spearman(pair_acc, phis),
                        top_pairs=sorted([dict(pair=f"{JUDGES[i]} + {JUDGES[j]}", acc=float(a), phi=p)
                                          for (i, j), a, p in zip(combinations(range(J), 2), pair_acc, phis)],
                                         key=lambda x: -x["phi"])[:5]),
        splits=splits, unanimous=dict(share=float(unan.mean()), wrong=float(unan_wrong.mean()),
                                      wrong_of_unanimous=float(unan_wrong.sum() / max(unan.sum(), 1)),
                                      wrong_accept=float((unan_wrong & (k == J)).mean()), wrong_reject=float((unan_wrong & (k == 0)).mean())),
        majority_acc=float((maj == gold).mean()), minority_right_items=minority_right,
        family=dict(within_agree=float(np.mean([x["agree"] for x in within])), across_agree=float(np.mean([x["agree"] for x in across])),
                    within_phi=float(np.mean([x["phi"] for x in within])), across_phi=float(np.mean([x["phi"] for x in across])),
                    within=within),
        lone_dissent={j: dict(n=v[1], right=float(v[0] / v[1])) for j, v in sorted(lone.items(), key=lambda kv: -kv[1][1])},
    )


def main():
    out = dict(same_wrong_answer=same_wrong_answer(TP / "bbeh_results/answers.jsonl"), judges={})
    s = out["same_wrong_answer"]
    print(f"[Kim] BBEH pilot: {s['n_questions']} questions x {s['n_models']} models; {s['both_wrong_pairs']} both-wrong pairs; "
          f"same wrong answer {s['same_wrong']:.1%} (chance {s['chance_same']:.1%})")
    for t, v in s["by_task"].items():
        print(f"   {t}: n={v['n']} same={v['same']:.0%}")
    for b in SOURCES:
        for cond in ["none", "human"] if b != "bffpair" else ["none", "human"]:
            try:
                V, gold = load(b, cond)
            except Exception:
                continue
            if len(V) < 30:
                continue
            r = judge_patterns(V, gold)
            out["judges"][f"{b}|{cond}"] = r
            c, e, u = r["co_error"], r["effective_votes"], r["unanimous"]
            print(f"\n[{b} {cond}] n={r['n']} majority {r['majority_acc']:.3f} | P(wrong) {c['mean_p_wrong']:.2f} -> "
                  f"P(wrong | other wrong) {c['mean_p_wrong_given_other_wrong']:.2f} (lift {c['mean_lift']:.2f}, phi {c['mean_phi']:.2f})")
            print(f"   effective votes of 8: Kish {e['kish']:.2f}, participation {e['participation_ratio']:.2f} | "
                  f"capability vs phi rho {r['capability']['spearman_pair_accuracy_vs_phi']:+.2f}")
            print(f"   unanimous {u['share']:.0%} of items, wrong on {u['wrong_of_unanimous']:.1%} of those "
                  f"(accept-bad {u['wrong_accept']:.1%}, reject-good {u['wrong_reject']:.1%} of all items) | minority-right {r['minority_right_items']:.1%}")
            print("   splits:", {k: (v["share"].__round__(2), None if v["majority_right"] is None else round(v["majority_right"], 2)) for k, v in r["splits"].items()})
            f = r["family"]
            print(f"   family agree within {f['within_agree']:.2f} vs across {f['across_agree']:.2f}; phi {f['within_phi']:.2f} vs {f['across_phi']:.2f}")
            print("   lone dissent right:", {j: f"{v['right']:.0%} of {v['n']}" for j, v in r["lone_dissent"].items()})
    (HERE / "results" / "agreement_patterns.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
