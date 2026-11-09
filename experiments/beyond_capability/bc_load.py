"""Load the beyond-capability outputs into flat per-judgment rows (shared by the analysis scripts)."""
import collections
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from bc_common import JUDGES, STRONG, norm_answer, same_answer  # noqa: E402
from data import bbeh_correct  # noqa: E402

POOL8 = ["qwen3.5-4b", "gpt-oss-20b", "nemotron3-nano-30b", "qwen3.5-9b", "qwen3.6-35b-a3b",
         "nemotron3-super-120b", "gpt-oss-120b", "deepseek-v3.1"]


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in open(p)] if p.exists() else []


def questions():
    return {q["id"]: q for q in jl(HERE / "inputs" / "questions.jsonl")}


def candidates():
    with gzip.open(HERE / "inputs" / "candidates.jsonl.gz", "rt") as f:
        return {c["cid"]: c for c in map(json.loads, f)}


def solve_stats(rows, qs):
    """qid -> dict(p = share of samples correct, maj = majority answer, share = its share, maj_ok, any_ok, norms)."""
    out = {}
    for r in rows:
        tgt = qs[r["qid"]]["target"]
        norms = [norm_answer(s["text"]) for s in r["samples"]]
        oks = [int(bbeh_correct(s["text"], tgt)) if n is not None else 0 for s, n in zip(r["samples"], norms)]
        groups = []
        for i, a in enumerate(norms):
            if a is None:
                continue
            for g in groups:
                if same_answer(g[0], a):
                    g[1].append(i)
                    break
            else:
                groups.append((a, [i]))
        if groups:
            best = max(groups, key=lambda g: len(g[1]))
            maj, share, maj_ok = best[0], len(best[1]) / len(norms), oks[best[1][0]]
        else:
            maj, share, maj_ok = None, 0.0, 0
        out[r["qid"]] = dict(p=float(np.mean(oks)), k=len(oks), maj=maj, share=share, maj_ok=maj_ok,
                             any_ok=int(any(oks)), norms=norms, oks=oks, first_ok=oks[0],
                             n_cut=sum(not s["clean"] for s in r["samples"]),
                             n_out=[s["n_out"] for s in r["samples"]])
    return out


def pool_answers():
    """Pool BBEH answers (thinking ON, 16K cap): (model, qid) -> answer text."""
    return {(r["model"], r["item"]): r["answer"] for r in jl(HERE.parent / "tinker_pool" / "bbeh_results" / "answers.jsonl")}


def think_solves(qs):
    """Thinking-ON own answer, one sample: Qwens = pool answer with cut-off ones rerun at 64K by the anchoring study;
    Nemotron-Super = our own run (262K). qid -> correct (0/1), or missing if it never finished."""
    pa = pool_answers()
    ext = {}
    for p in sorted((HERE.parent / "anchoring_early_answer" / "out").glob("extended*.jsonl")):
        for r in jl(p):
            if r.get("kind") == "solve" and r.get("bench") == "bbeh":
                ext[(r["model"], r["qid"])] = r
    out = collections.defaultdict(dict)
    for j in JUDGES:
        if j.startswith("qwen"):
            for q in qs:
                t = pa.get((j, q))
                if (j, q) in ext:
                    t = ext[(j, q)]["text"] if ext[(j, q)]["clean"] else None
                elif t is not None and norm_answer(t) is None:
                    t = None  # cut off at 16K and never rerun
                if t is not None:
                    out[j][q] = int(bbeh_correct(t, qs[q]["target"]))
        else:
            for r in jl(OUT / f"solves_{j}@think.jsonl"):
                s = r["samples"][0]
                if s["clean"]:
                    out[j][r["qid"]] = int(bbeh_correct(s["text"], qs[r["qid"]]["target"]))
    return out


def pool_difficulty(qs):
    """Share of the 8 pool models whose (thinking-on) answer is correct -- an outside measure of difficulty."""
    pa = pool_answers()
    return {q: float(np.mean([bbeh_correct(pa.get((m, q)) or "", qs[q]["target"]) for m in POOL8])) for q in qs}


def judgments(judge, fill=None):
    """Rows: judge, cid, qid, cond, gold, v (sample-0 verdict, GLM-filled), share (vote share over samples)."""
    fill = fill if fill is not None else {r["cache_key"]: r["verdict"] for r in jl(OUT / "fill_glm.jsonl")}
    rows = []
    seen = set()
    allr = [r for p in sorted(OUT.glob(f"judge_{judge}[._]*")) if p.suffix == ".jsonl" for r in jl(p)]
    for r in allr:
        if r["cache_key"] in seen:
            continue
        seen.add(r["cache_key"])
        vs = []
        for i, s in enumerate(r["samples"]):
            v = s["verdict"]
            if v is None:
                f = fill.get(f"{r['cache_key']}|{i}")
                v = {"CORRECT": 1, "INCORRECT": 0}.get(f)
            vs.append(v)
        known = [v for v in vs if v is not None]
        rows.append(dict(judge=judge, cid=r["cid"], qid=r["qid"], cond=r["cond"], gold=r["gold"], v=vs[0],
                         share=float(np.mean(known)) if known else None, n_out=r["samples"][0]["n_out"],
                         clean=r["samples"][0]["clean"], n_in=r["n_in"]))
    return rows


# ----------------------------------------------------------------------------- metrics
def kappa(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    if len(y) == 0:
        return float("nan")
    po = (y == p).mean()
    pe = y.mean() * p.mean() + (1 - y.mean()) * (1 - p.mean())
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def within_auc(y, s, groups):
    by = collections.defaultdict(lambda: ([], []))
    for yi, si, g in zip(y, s, groups):
        if si is not None and si == si:
            by[g][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        for a in pos:
            for b in neg:
                num += 1.0 if a > b else 0.5 if a == b else 0.0
                den += 1
    return (num / den if den else float("nan")), int(den)


def metrics(rows, key="v", score=None):
    """rows with gold, qid and a 0/1 verdict under `key` (None = unparseable -> counted as reject)."""
    R = [r for r in rows]
    if not R:
        return dict(n=0)
    y = np.array([r["gold"] for r in R])
    v = np.array([0 if r[key] is None else r[key] for r in R], float)
    tpr = v[y == 1].mean() if (y == 1).any() else float("nan")
    fpr = v[y == 0].mean() if (y == 0).any() else float("nan")
    wq, npairs = within_auc(y, [r[score] if score else (0 if r[key] is None else r[key]) for r in R],
                            [r["qid"] for r in R])
    return dict(n=len(R), n_pos=int((y == 1).sum()), n_neg=int((y == 0).sum()), acc=float((v == y).mean()),
                tpr=float(tpr), fpr=float(fpr), bal=float((tpr + 1 - fpr) / 2), kappa=float(kappa(y, v)),
                wq=wq, pairs=npairs)


def boot_ci(rows, fn, n=1000, seed=0):
    """95% interval of fn(rows), resampling whole questions."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["qid"]].append(r)
    keys = list(by)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        smp = [r for k in rng.choice(len(keys), len(keys)) for r in by[keys[k]]]
        x = fn(smp)
        if x == x:
            vals.append(x)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (float("nan"),) * 2
