"""Intervention: a hidden-state probe as the verdict, split by whether the judge can solve the question.

Reuses the anchoring study's position-A captures (read-only): out_probe/<judge>/hidden.npy + meta.jsonl, i.e. the
judge's residual stream after reading the question and candidate, before it writes anything. A logistic-regression
probe at the layer the anchoring study found best is trained with whole questions held out (5 folds), so every
score is out-of-fold. We then compare, on solved vs unsolved questions:
  - the judge's spoken verdict (pool transcript; cut-off ones rerun),
  - the probe score,
using within-question AUROC (only candidates of the same question are compared) and balanced accuracy at the
threshold that matches the spoken verdict's overall acceptance rate.

Solved labels: BBEH = this study's thinking-off 5-sample majority answer; RB2 Math / JudgeBench = the anchoring
study's single solve (out/existing_rows.jsonl).

  python3 experiments/beyond_capability/probe_split.py
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ANC = HERE.parent / "anchoring_early_answer"
sys.path.insert(0, str(ANC))
sys.path.insert(0, str(HERE))
from probes import cv_scores, qid as probe_qid  # noqa: E402
from bc_load import OUT, jl, questions, solve_stats, within_auc  # noqa: E402
from bc_common import has_final  # noqa: E402


# best layer per judge x benchmark, from the anchoring study's out_probe/<judge>/probes.md (chosen on all items)
BEST_LAYER = {"qwen3.5-4b": {"bbeh": 25, "rb2math": 32, "judgebench": 22},
              "qwen3.5-9b": {"bbeh": 19, "rb2math": 31, "judgebench": 28}}


def main():
    qs = questions()
    ex = {(r["judge"], r["item"]): r for r in jl(OUT / "existing_rows.jsonl")}
    rows_anc = {(r["judge"], r["bench"], r["item"]): r for r in json.load(open(ANC / "out" / "rows.json"))}
    pool = {(r["model"], r["item"]): r["answer"] for r in jl(HERE.parent / "tinker_pool" / "bbeh_results" / "answers.jsonl")}
    L = ["| Judge | Benchmark | Questions | n | pairs | spoken verdict: within-Q AUROC | probe: within-Q AUROC | spoken: balanced acc | probe: balanced acc (same leniency) |",
         "|---|---|---|---|---|---|---|---|---|"]
    res = {}
    for judge in ("qwen3.5-4b", "qwen3.5-9b"):
        d = ANC / "out_probe" / judge
        H = np.load(d / "hidden.npy", mmap_mode="r")
        meta = [json.loads(l) for l in open(d / "meta.jsonl")]
        S = solve_stats(jl(OUT / f"solves_{judge}.jsonl"), qs)
        for bench, setname in (("bbeh", "BBEH"), ("rb2math", "RB2 Math"), ("judgebench", "JudgeBench (pairwise)")):
            layer = BEST_LAYER[judge][bench]
            idx, solved, spoken, groups = [], [], [], []
            for i, m in enumerate(meta):
                if m["bench"] != bench:
                    continue
                if bench == "bbeh":
                    q, exam = m["item_id"].split("|")
                    if not has_final(pool.get((exam, q))) or exam == judge or q not in S:
                        continue
                    sv = S[q]["maj_ok"]
                    lab = rows_anc.get((judge, bench, m["item_id"]))
                    sp = None if lab is None else lab.get("spoken")
                else:
                    r = ex.get((judge, m["item_id"]))
                    if r is None or r["solved"] is None:
                        continue
                    sv = r["solved"]
                    sp = r["verdict"] if bench == "rb2math" else None
                idx.append(i)
                solved.append(sv)
                spoken.append(np.nan if sp is None else sp)
                groups.append(probe_qid(bench, m["item_id"]))
            idx = np.array(idx)
            y = np.array([meta[i]["gold"] for i in idx])
            groups = np.array(groups)
            solved = np.array(solved)
            spoken = np.array(spoken, float)
            margin = np.array([meta[i]["margin"] for i in idx])
            p = cv_scores(np.asarray(H[idx, layer], np.float32), y, groups)
            if bench == "judgebench":  # pairwise: gold = A better; the margin/probe is toward A. Spoken from rows.
                spoken = margin.copy()  # use the judge's own A-vs-B margin at A as its verdict score
            ok = ~np.isnan(spoken)
            acc_rate = np.mean(spoken[ok] > (0 if bench == "judgebench" else 0.5)) if ok.any() else 0.5
            thr = np.quantile(p, 1 - acc_rate)
            for sv, name in ((1, "solved"), (0, "unsolved")):
                sel = solved == sv
                if bench == "judgebench":  # one item per question: plain AUROC of "A is better"
                    from sklearn.metrics import roc_auc_score
                    a_sp, a_pr = roc_auc_score(y[sel], spoken[sel]), roc_auc_score(y[sel], p[sel])
                    n_pairs = int((y[sel] == 1).sum() * (y[sel] == 0).sum())
                else:
                    a_sp, n_pairs = within_auc(y[sel], spoken[sel], groups[sel])
                    a_pr, _ = within_auc(y[sel], p[sel], groups[sel])

                def bal(v, yy):
                    return (np.mean(v[yy == 1]) + 1 - np.mean(v[yy == 0])) / 2
                sp_v = spoken[sel] > (0 if bench == "judgebench" else 0.5)
                b_sp = bal(sp_v[ok[sel]], y[sel][ok[sel]])
                b_pr = bal((p[sel] > thr), y[sel])
                res[(judge, bench, name)] = dict(n=int(sel.sum()), pairs=n_pairs, sp_wq=a_sp, pr_wq=a_pr, sp_bal=b_sp, pr_bal=b_pr)
                lbl = {"bbeh": "BBEH", "rb2math": "RB2 Math", "judgebench": "JudgeBench"}[bench]
                sp_name = "verdict at A" if bench == "judgebench" else "spoken"
                L.append(f"| {judge} | {lbl} (layer {layer}) | {name} | {sel.sum()} | {n_pairs} | {a_sp:.2f}"
                         f"{' (' + sp_name + ')' if bench == 'judgebench' else ''} | {a_pr:.2f} | {b_sp:.2f} | {b_pr:.2f} |")
    (OUT / "probe_split.md").write_text("\n".join(L) + "\n")
    json.dump({"|".join(k): v for k, v in res.items()}, open(OUT / "probe_split.json", "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
