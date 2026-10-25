"""Every number in this folder, computed from the saved verdicts in runs/. Never calls a model.

Inputs, all in this folder:
  runs/<judge>__<prompt>.jsonl        one verdict per row, written by notebook/grading_like_experts.ipynb
  data/verdicts.parquet               Kensho's VERDICTS: three expert votes per answer
  data/bffbench.parquet               Kensho's BFF-Bench: one reference per question turn
  data/gpt_oss_120b_rejections_read.csv   a hand reading of the 23 correct answers gpt-oss-120b rejected with the rules
annotator() caches its result in .cache/annotator.json, keyed by the run files' names, sizes and times. Delete .cache/ to rebuild.
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
DATA = ROOT / "data"
CACHE = ROOT / ".cache"
B = 2000  # bootstrap resamples over the questions for a difference in kappa

ANNO_JUDGES = ["qwen3.7-flash", "gpt-4.1-mini", "deepseek-v3.1", "gpt-oss-20b", "gpt-oss-120b"]  # most lenient first (false accepts, standard prompt)
GROUPS = {"unanimous": "all 3 agree", "two_plus_unsure": "2 agree + 1 not sure", "split": "2-1 split"}


def _key(folder: Path) -> str:
    return "|".join(f"{p.name}:{p.stat().st_size}:{int(p.stat().st_mtime)}" for p in sorted(folder.glob("*.jsonl")))


def _cached(name: str, folder: Path, fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{name}.json"
    k = _key(folder)
    if p.exists():
        d = json.loads(p.read_text())
        if d.get("_key") == k:
            return d
    d = fn(); d["_key"] = k
    p.write_text(json.dumps(d, indent=1, default=float))
    return d


def runs() -> pd.DataFrame:
    """Every verdict in runs/, with judge and prompt split out of the row's arm field ("<judge>|<prompt>")."""
    rows = [json.loads(line) for p in sorted(RUNS.glob("*.jsonl")) for line in p.read_text().splitlines()]
    D = pd.DataFrame(rows)
    D[["judge", "arm"]] = D.arm.str.split("|", expand=True)
    return D


def items() -> pd.DataFrame:
    """The 799 answers: every BFF-Bench answer where at least 2 of 3 experts agree, the majority vote as the label, minus
    conversation fc9858ab, whose VERDICTS record stores the turn-1 reference where the question should be."""
    V = pd.read_parquet(DATA / "verdicts.parquet"); V = V[V.dataset == "bffbench"]
    refs = {str(r.uid): [str(x) for x in r.references] for r in pd.read_parquet(DATA / "bffbench.parquet").itertuples()}
    votes = V.groupby(["cid", "turn"]).label.agg(list); rows = []
    for r in V.groupby(["cid", "turn"]).first().reset_index().itertuples():
        c = collections.Counter(votes[(r.cid, r.turn)]); C, I = c["Correct"], c["Incorrect"]
        if max(C, I) < 2 or r.qid == "fc9858ab":
            continue
        conv = json.dumps([{"role": m["role"], "content": m["content"]} for m in r.conv]); ref = refs[str(r.qid)][int(r.turn) - 1]
        rows.append(dict(item_id=f"{r.cid}-t{r.turn}", qid=r.qid, cid=r.cid, turn=int(r.turn), gold=int(C > I), chars=len(conv) + len(ref),
                         votes="; ".join(sorted(votes[(r.cid, r.turn)])),
                         group="unanimous" if max(C, I) == 3 else ("two_plus_unsure" if min(C, I) == 0 else "split")))
    return pd.DataFrame(rows).set_index("item_id")


def boot(fn, qids, b=B, seed=0):
    """Point estimate and 95% interval of fn(index array), resampling questions with replacement."""
    rng = np.random.default_rng(seed); q = np.asarray(qids); uq = np.unique(q); idx = {u: np.where(q == u)[0] for u in uq}
    est = float(fn(np.arange(len(q))))
    bs = [fn(np.concatenate([idx[u] for u in rng.choice(uq, len(uq))])) for _ in range(b)]
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    return [est, float(lo), float(hi)]


def kappa(g, v):
    """Cohen's kappa between two 0/1 vectors."""
    g, v = np.asarray(g, float), np.asarray(v, float)
    po = (g == v).mean(); pe = g.mean() * v.mean() + (1 - g.mean()) * (1 - v.mean())
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def rejections_read() -> pd.DataFrame:
    """Hand reading (Oct 16, 2026) of every correct answer gpt-oss-120b rejected with the rules but accepted on the standard
    prompt, on the 456 answers all three experts agreed on: one reason per answer, and whether its reasoning doubts the reference."""
    return pd.read_csv(DATA / "gpt_oss_120b_rejections_read.csv")


def annotator() -> dict:
    """Every number on the page and in results/, cached until a run file changes."""
    return _cached("annotator", RUNS, _annotator)


def _annotator() -> dict:
    It = items(); gold, qid, grp = It.gold.to_dict(), It.qid.to_dict(), It.group.to_dict()
    D = runs(); D = D[D.item_id.isin(gold)]
    D["gold"] = D.item_id.map(gold); D["qid"] = D.item_id.map(qid); D["group"] = D.item_id.map(grp)
    D["v"] = D.verdict.where(D.verdict != -1, 1 - D.gold)  # strict: an unparsed verdict is scored as the wrong one
    D0 = D[D.run == 0]
    out = dict(n_items=int(len(It)), n_questions=int(It.qid.nunique()), groups={k: int(v) for k, v in It.group.value_counts().items()},
               share_correct=float(It.gold.mean()), n_question_turns=int(It.groupby([It.qid, It.index.str[-1]]).ngroups),
               cells={}, deltas={}, by_group={}, deltas_by_group={})

    def summary(x, b=1000):
        gg, vv, qq = x.gold.values, x.v.values, x.qid.values
        return dict(kappa=boot(lambda ii: kappa(gg[ii], vv[ii]), qq, b=b), fpr=float((vv[gg == 0] == 1).mean()), fnr=float((vv[gg == 1] == 0).mean()), n=int(len(x)))

    for (j, a), x in D0.groupby(["judge", "arm"]):
        c = summary(x)
        c.update(parsed=float((x.verdict != -1).mean()), cost=float(pd.to_numeric(x.cost, errors="coerce").fillna(0).mean()),
                 n_out=float(pd.to_numeric(x.n_out, errors="coerce").mean()))
        out["cells"][f"{j}|{a}"] = c
        out["by_group"][f"{j}|{a}"] = {g: summary(y, b=500) for g, y in x.groupby("group")}

    def paired(x, y):
        ix = x.index.intersection(y.index); x, y = x.loc[ix], y.loc[ix]; g_, qq = x.gold.values, x.qid.values
        return boot(lambda ii: kappa(g_[ii], y.v.values[ii]) - kappa(g_[ii], x.v.values[ii]), qq)

    for j in D0.judge.unique():
        arms = set(D0[D0.judge == j].arm)
        for a, b in (("STD", "GUIDE"), ("GUIDE", "GUIDE_NO2"), ("STD", "GUIDE_NO2")):
            if {a, b} <= arms:
                x = D0[(D0.judge == j) & (D0.arm == a)].set_index("item_id"); y = D0[(D0.judge == j) & (D0.arm == b)].set_index("item_id")
                out["deltas"][f"{j}|{b}-{a}"] = dict(orig=paired(x, y))
                out["deltas_by_group"][f"{j}|{b}-{a}"] = {g: paired(x[x.group == g], y[y.group == g]) for g in GROUPS
                                                          if (x.group == g).any() and (y.group == g).any()}

    # rerun noise: qwen3.7-flash graded every answer twice with the standard prompt
    n = D[(D.judge == "qwen3.7-flash") & (D.arm == "STD")].pivot_table(index="item_id", columns="run", values="v").dropna()
    gq = np.array([gold[i] for i in n.index])
    out["noise"] = dict(flip=float((n[0] != n[1]).mean()), k0=float(kappa(gq, n[0])), k1=float(kappa(gq, n[1])), n=int(len(n)))

    # correct answers gpt-oss accepted on the standard prompt but rejected with the rules: "flips" on the 456 unanimous answers
    # (the hand-read set), "flips_all" on every answer
    V = D0.pivot_table(index="item_id", columns=["judge", "arm"], values="verdict", aggfunc="first")
    T = D0.set_index(["item_id", "judge", "arm"]).text.fillna("")
    cites = lambda t, r: r in re.findall(r"rule\s*\(?\s*([1-5])\s*\)?", t.lower())  # noqa: E731
    for key, pool in (("flips", [i for i in V.index if grp[i] == "unanimous"]), ("flips_all", list(V.index))):
        out[key] = {}
        for j in ("gpt-oss-120b", "gpt-oss-20b"):
            ids = [i for i in pool if gold[i] == 1 and V.loc[i, (j, "STD")] == 1 and V.loc[i, (j, "GUIDE")] == 0]
            out[key][j] = dict(ids=ids, n=len(ids), n_correct=int(sum(gold[i] == 1 for i in pool)),
                               cite={r: int(sum(cites(T[(i, j, "GUIDE")], r) for i in ids)) for r in "12345"},
                               no_rule=int(sum(not any(cites(T[(i, j, "GUIDE")], r) for r in "12345") for i in ids)),
                               back_no2=int(sum(V.loc[i, (j, "GUIDE_NO2")] == 1 for i in ids)),
                               deepseek_accepts=int(sum(V.loc[i, ("deepseek-v3.1", "GUIDE")] == 1 for i in ids)))
    out["prompt_chars"] = float(It.chars.mean())  # mean prompt length in characters, for the cost estimate of the self-hosted judges
    return out
