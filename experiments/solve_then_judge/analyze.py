#!/usr/bin/env python3
"""
Solve-then-judge on BFF-Bench (core version): none vs self vs human, 8 Tinker judges.

Final metric = agreement with the human label (VERDICTS, 2-of-3 rule; 808 responses). The judges' own answers
(step 2) and their LLM-graded "solved" labels (step 3) are only used to split the analysis.

Solved label per (judge, question turn): the two graders (gpt-oss-120b and DeepSeek-V3.1, each with the expert
reference) must agree, otherwise "uncertain". For the two gpt-oss judges, DeepSeek's label alone is used, so
gpt-oss-120b never grades its own family's answers.

  uv run python experiments/solve_then_judge/analyze.py
Reads tinker_pool/bff_results_max4096_majority/judgments.jsonl and tinker_pool/bff_results/grades.jsonl;
writes experiments/solve_then_judge/results/summary.md and metrics.json.
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TP = HERE.parent / "tinker_pool"
sys.path.insert(0, str(TP))
sys.path.insert(0, str(HERE.parent / "jev_bff"))
JUDGES = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-9b", "qwen3.5-4b",
          "nemotron3-super-120b", "nemotron3-nano-30b"]


def kappa(y, v):
    y, v = np.asarray(y, float), np.asarray(v, float)
    pe = y.mean() * v.mean() + (1 - y.mean()) * (1 - v.mean())
    return float(((y == v).mean() - pe) / (1 - pe)) if pe < 1 else None


def boot(diff, groups, n=2000, seed=0):
    g = pd.Series(diff).groupby(np.asarray(groups))
    s, c = g.sum().values, g.count().values
    idx = np.random.default_rng(seed).integers(0, len(s), (n, len(s)))
    m = s[idx].sum(1) / c[idx].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def gold_labels():
    from run_jev_bff import load_data
    v, b = load_data(None, None, "bff")
    v = v[v["dataset"].astype(str).str.lower() == "bffbench"]
    to_uid = {}
    for r in b.itertuples():
        to_uid[str(r.uid)] = str(r.uid)
        if getattr(r, "question_id", None) not in (None, "None"):
            to_uid[str(r.question_id)] = str(r.uid)
    rows = []
    for (qid, cid, turn, model), g in v.groupby(["qid", "cid", "turn", "model"]):
        votes = [str(x).lower() for x in g["label"]]
        c, i = votes.count("correct"), votes.count("incorrect")
        gold = 1 if c >= 2 else 0 if i >= 2 else None
        if gold is None:
            continue
        rows.append(dict(key=f"{cid}-t{int(turn)}|{model}", uid=to_uid.get(str(qid), str(qid)), turn=int(turn),
                         gold=gold, unanimous=len(set(votes)) == 1))
    return pd.DataFrame(rows)


def solved_labels():
    g = pd.DataFrame([json.loads(l) for l in open(TP / "bff_results/grades.jsonl")])
    w = g.pivot_table(index=["model", "item", "turn"], columns="grader", values="correct").reset_index()
    def lab(r):
        if r.model.startswith("gpt-oss"):
            return r["deepseek-v3.1"]
        return r["gpt-oss-120b"] if r["gpt-oss-120b"] == r["deepseek-v3.1"] else np.nan
    w["solved"] = w.apply(lab, axis=1)
    return w.rename(columns={"model": "judge", "item": "uid"})[["judge", "uid", "turn", "solved"]]


def main():
    G = gold_labels()
    rows = []
    for line in open(TP / "bff_results_max4096_majority/judgments.jsonl"):
        r = json.loads(line)
        rows.append(dict(key=f"{r['item_id']}|{r['examinee']}", judge=r["judge"], cond=r["condition"],
                         verdict=int((r.get("vote_share") or 0) > 0.5), parsed=int(r.get("n_parsed", 0) > 0)))
    J = pd.DataFrame(rows).drop_duplicates(["key", "judge", "cond"], keep="last")
    d = J.merge(G, on="key")
    d["agree"] = (d.verdict == d.gold).astype(int)
    S = solved_labels()
    S["uid"], S["turn"] = S.uid.astype(str), S.turn.astype(int)
    d = d.merge(S, on=["judge", "uid", "turn"], how="left")

    out, L = {}, ["# Solve-then-judge on BFF-Bench (core): none vs self vs human", "",
                  f"{G.shape[0]} responses with a 2-of-3 human label ({int(G.unanimous.sum())} unanimous). 8 Tinker judges, "
                  "1 sample, T = 0.7, max 4,096 tokens. Agreement = verdict matches the human label. "
                  "Δ = self − none on the same responses, 95% CI resampling whole conversations.", "",
                  "## 1. Headline", "",
                  "| Judge | n | none | self | human | Δ self − none | 95% CI | κ none | κ self | parsed none / self |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
    for j in JUDGES:
        w = d[d.judge == j].pivot_table(index="key", columns="cond", values="agree")
        if not {"none", "self"} <= set(w.columns):
            continue
        p = w[["none", "self"]].dropna()
        groups = p.index.str.split("-t").str[0]
        diff = (p["self"] - p["none"]).values
        ci = boot(diff, groups)
        gold = d.drop_duplicates("key").set_index("key").gold
        V = d[d.judge == j].pivot_table(index="key", columns="cond", values="verdict").loc[p.index]
        par = d[d.judge == j].groupby("cond").parsed.mean()
        hum = w["human"].dropna().mean() if "human" in w else np.nan
        out[j] = dict(n=len(p), none=float(p["none"].mean()), self=float(p["self"].mean()), human=float(hum),
                      diff=float(diff.mean()), ci=ci, k_none=kappa(gold.loc[p.index], V["none"]),
                      k_self=kappa(gold.loc[p.index], V["self"]))
        o = out[j]
        L.append(f"| {j} | {o['n']} | {100*o['none']:.1f} | {100*o['self']:.1f} | {100*o['human']:.1f} | "
                 f"{100*o['diff']:+.1f} | [{100*ci[0]:+.1f}, {100*ci[1]:+.1f}] | {o['k_none']:.3f} | {o['k_self']:.3f} | "
                 f"{par.get('none', np.nan):.2f} / {par.get('self', np.nan):.2f} |")
    mean_d = np.mean([o["diff"] for o in out.values()])
    L += ["", f"Mean Δ over judges: {100*mean_d:+.1f} points.", "",
          "## 2. When the judge solved the question vs failed it", "",
          "Solved = the judge's own answer was graded correct (both graders agree; DeepSeek only for gpt-oss judges). "
          "Uncertain items are left out.", "",
          "| Judge | solved: n | none | self | Δ | failed: n | none | self | Δ |", "|---|---|---|---|---|---|---|---|---|"]
    split = {}
    for j in out:
        w = d[d.judge == j].pivot_table(index="key", columns="cond", values="agree")[["none", "self"]].dropna()
        sv = d[(d.judge == j)].drop_duplicates("key").set_index("key").solved.loc[w.index]
        cells = []
        for s in (1, 0):
            q = w[sv == s]
            cells += [len(q), q["none"].mean(), q["self"].mean(), (q["self"] - q["none"]).mean()]
        split[j] = cells
        L.append(f"| {j} | {cells[0]} | {100*cells[1]:.1f} | {100*cells[2]:.1f} | {100*cells[3]:+.1f} | "
                 f"{cells[4]} | {100*cells[5]:.1f} | {100*cells[6]:.1f} | {100*cells[7]:+.1f} |")
    L += ["", "## 3. Flips between none and self", "",
          "| Judge | right → wrong | wrong → right | right → wrong when own answer failed | wrong → right when own answer solved |",
          "|---|---|---|---|---|"]
    flips = {}
    for j in out:
        w = d[d.judge == j].pivot_table(index="key", columns="cond", values="agree")[["none", "self"]].dropna()
        sv = d[(d.judge == j)].drop_duplicates("key").set_index("key").solved.loc[w.index]
        rw, wr = (w["none"] == 1) & (w["self"] == 0), (w["none"] == 0) & (w["self"] == 1)
        flips[j] = [int(rw.sum()), int(wr.sum()), int((rw & (sv == 0)).sum()), int((wr & (sv == 1)).sum())]
        L.append(f"| {j} | " + " | ".join(str(x) for x in flips[j]) + " |")
    L += ["", "## 4. Unanimous vs split-vote responses", "", "| Judge | Δ unanimous | Δ split |", "|---|---|---|"]
    for j in out:
        w = d[d.judge == j].pivot_table(index="key", columns="cond", values="agree")[["none", "self"]].dropna()
        un = d.drop_duplicates("key").set_index("key").unanimous.loc[w.index]
        L.append(f"| {j} | {100*(w['self']-w['none'])[un].mean():+.1f} | {100*(w['self']-w['none'])[~un].mean():+.1f} |")
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results/summary.md").write_text("\n".join(L) + "\n")
    (HERE / "results/metrics.json").write_text(json.dumps(dict(headline=out, split=split, flips=flips), indent=1))
    print("\n".join(L))


if __name__ == "__main__":
    main()
