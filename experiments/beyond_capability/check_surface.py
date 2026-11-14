"""Does the judge direction carry more than surface clues?
Within-question ranking (right vs wrong answers to the same question, 0.50 = chance) of:
  knows      held-out judge-direction score (out_checks/dump_<bench>.jsonl, from azure/dir_dump.py on the cluster)
  says       the unedited verdict score
  surface    logistic regression on surface clues of the answer text (length, lines, hedging words, digits, which model
             wrote it, the chosen letter), question-centred, trained on one half of the questions and scored on the other
  consensus  share of the question's other candidate answers that reach the same final answer (label-free)
  knows beyond surface   the direction score after removing what the surface clues predict (within question, cross-fitted)
By judge x solved group, for MMLU-Redux and MATH.

  python3 experiments/beyond_capability/check_surface.py   -> out_checks/surface_<bench>.md
"""
import ast
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression

HERE = Path(__file__).resolve().parent
OUT = HERE / "out_checks"
HEDGE = re.compile(r"\b(wait|however|actually|alternatively|but|hmm|re-?check|mistake|let me)\b", re.I)
NAME = {"qwen3.5-9b": "Qwen-9B", "llama3.1-8b": "Llama-8B"}


def answer_text(msgs):
    m = ast.literal_eval(msgs) if isinstance(msgs, str) else msgs
    c = m[-1]["content"]
    a = c.split("[ASSISTANT'S ANSWER]", 1)[1]
    return a.rsplit("Is the assistant's final answer correct?", 1)[0]


def features(items):
    srcs = sorted({r["src"] for r in items.values()})
    letters = sorted({str(r.get("letter")) for r in items.values()}) if len({str(r.get("letter")) for r in items.values()}) <= 12 else []
    feats = {}
    for aid, r in items.items():
        t = answer_text(r["messages"])
        f = [np.log1p(len(t)), np.log1p(t.count("\n")), len(HEDGE.findall(t)) / max(1, len(t) / 1000),
             sum(ch.isdigit() for ch in t) / max(1, len(t)), np.log1p(len(str(r.get("letter", ""))))]
        f += [float(r["src"] == s) for s in srcs] + [float(str(r.get("letter")) == L) for L in letters]
        feats[aid] = f
    return feats


def consensus(items):
    by = defaultdict(list)
    for aid, r in items.items():
        by[r["qid"]].append((aid, str(r.get("letter"))))
    out = {}
    for q, xs in by.items():
        c = Counter(a for _, a in xs)
        for aid, a in xs:
            out[aid] = (c[a] - 1) / max(1, len(xs) - 1)
    return out


def qcenter(X, q):
    X = X.astype(float).copy()
    for g in set(q):
        k = q == g
        X[k] -= X[k].mean(0)
    return X


def wq_auroc(score, y, q, keep):
    pts = n = 0.0
    by = defaultdict(lambda: ([], []))
    for s, yy, qq, k in zip(score, y, q, keep):
        if k:
            by[qq][0 if yy else 1].append(s)
    for R, W in by.values():
        if R and W:
            R, W = np.array(R)[:, None], np.array(W)[None, :]
            pts += (R > W).sum() + 0.5 * (R == W).sum()
            n += R.size * W.size
    return pts / n if n else float("nan")


def main():
    for bench, itemf in (("mmlu", "mmlu_full_items.jsonl.gz"), ("math", "math_full_items.jsonl.gz")):
        items = {}
        for line in gzip.open(HERE / "inputs" / itemf):
            r = json.loads(line)
            items[r["aid"]] = r
        F, C = features(items), consensus(items)
        sols = json.load(open(OUT / f"sol_{bench}.json"))
        dump = [json.loads(x) for x in open(OUT / f"dump_{bench}.jsonl")]
        lines = [f"## {bench}", "",
                 "| Judge | Questions | n answers | Knows (direction) | Says (verdict) | Surface clues | Consensus | Knows beyond surface | corr(direction, surface) |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for m in ("qwen3.5-9b", "llama3.1-8b"):
            rows = [r for r in dump if r["model"] == m and r["aid"] in items]
            y = np.array([r["gold"] for r in rows])
            q = np.array([r["qid"] for r in rows])
            h1 = np.array([r["half"] == "h1" for r in rows])
            d = np.array([r["dirscore"] for r in rows])
            v = np.array([r["verdict"] if r["verdict"] is not None else np.nan for r in rows])
            X = qcenter(np.array([F[r["aid"]] for r in rows]), q)
            X = (X - X.mean(0)) / (X.std(0) + 1e-9)
            cons = np.array([C[r["aid"]] for r in rows])
            surf = np.zeros(len(y))
            resid = np.zeros(len(y))
            dc = qcenter(d[:, None], q)[:, 0]
            for tr, te in ((h1, ~h1), (~h1, h1)):
                clf = LogisticRegression(C=1.0, max_iter=2000).fit(X[tr], y[tr])
                surf[te] = clf.decision_function(X[te])
                lr = LinearRegression().fit(X[tr], dc[tr])
                resid[te] = dc[te] - lr.predict(X[te])
            sol = sols.get(m, {})
            for gname, keep in (("all", np.ones(len(y), bool)),
                                ("solved", np.array([sol.get(x, -1) == 1 for x in q])),
                                ("not solved", np.array([sol.get(x, -1) == 0 for x in q]))):
                ok = keep & ~np.isnan(v)
                if ok.sum() < 50:
                    continue
                r_ds = np.corrcoef(dc[ok], qcenter(surf[:, None], q)[ok, 0])[0, 1]
                lines.append(f"| {NAME[m]} | {gname} | {ok.sum()} | {wq_auroc(d, y, q, ok):.3f} | {wq_auroc(v, y, q, ok):.3f} | "
                             f"{wq_auroc(surf, y, q, ok):.3f} | {wq_auroc(cons, y, q, ok):.3f} | {wq_auroc(resid, y, q, ok):.3f} | {r_ds:.2f} |")
        out = "\n".join(lines)
        (OUT / f"surface_{bench}.md").write_text(out + "\n")
        print(out + "\n")


if __name__ == "__main__":
    main()
