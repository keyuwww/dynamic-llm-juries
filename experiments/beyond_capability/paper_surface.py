"""Surface controls for the direction readout (reviewer D3): does the direction's gain survive once answer length,
formatting and confidence wording are regressed out?

Features of the judged answer text (the [ASSISTANT'S ANSWER] block of the judge prompt): log characters, log lines,
bold markers, LaTeX dollar signs, "Step" headers, hedge words, confidence words, self-correction words, and the
answering model's final-answer line format. All fits are within question (features and scores demeaned per question)
and cross-fit over the paper's two question halves (seed 0):
  surface      ranking by a linear model of correctness on the features alone
  dir_resid    ranking by the direction score with its linear prediction from the features removed
Pooled with the synchronised bootstrap (sync_stats.py).

  python3 experiments/beyond_capability/paper_surface.py -> out_paper/surface_check.json
"""
import gzip
import json
import re
from collections import defaultdict

import numpy as np

import allpairs_analyze as A
import sync_stats as S
from paper_data import BIG, pool_sets

FILES = {"mmlu": "mmlu_full_items.jsonl.gz", "math": "math_full_items.jsonl.gz", "bbeh": "bbeh_items.jsonl.gz"}
HEDGE = r"\b(maybe|might|perhaps|possibly|probably|likely|approximately|i think|i believe|not sure|unclear|assum\w*)\b"
CONF = r"\b(clearly|definitely|certainly|obviously|indeed|undoubtedly|must be)\b"
CORR = r"\b(wait|actually|however|re-?check|double-?check|let me re\w*|mistake|correction)\b"
NAMES = ["log_chars", "log_lines", "bold", "dollars", "steps", "hedge", "conf", "selfcorr", "answer_line"]


def answer_text(r):
    t = r["messages"][-1]["content"]
    i = t.find("[ASSISTANT'S ANSWER]")
    j = t.rfind("Is the assistant's final answer correct?")
    return t[i + len("[ASSISTANT'S ANSWER]"): j] if i >= 0 and j > i else t


def feats(t):
    lo = t.lower()
    return [np.log1p(len(t)), np.log1p(t.count("\n")), t.count("**"), t.count("$"), len(re.findall(r"\bstep\b", lo)),
            len(re.findall(HEDGE, lo)), len(re.findall(CONF, lo)), len(re.findall(CORR, lo)),
            float(bool(re.search(r"the answer is[: ]", lo)))]


def demean(x, q):
    x = x.astype(float).copy()
    for g in set(q):
        k = q == g
        x[k] -= x[k].mean(0)
    return x


METH = ("verdict", "direct", "surface", "dir_resid")


def perq_split(rows, key):
    """{qid: [num, den] for all / same-model / different-model right-vs-wrong pairs}"""
    by = defaultdict(list)
    for r in rows:
        by[r["qid"]].append(r)
    out = {}
    for g, rs in by.items():
        P = [r for r in rs if r["gold"] == 1]
        N = [r for r in rs if r["gold"] == 0]
        if not P or not N:
            continue
        v = np.zeros(6)
        for a in P:
            for b in N:
                w = 1.0 if a[key] > b[key] else 0.5 if a[key] == b[key] else 0.0
                k = 2 if a["src"] == b["src"] else 4
                v[[0, 1, k, k + 1]] += [w, 1, w, 1]
        out[g] = v
    return out


def main():
    F = {}
    for b, f in FILES.items():
        for l in gzip.open(A.HERE / "inputs" / f, "rt"):
            r = json.loads(l)
            if r["mode"] == "J":
                F[r["aid"]] = feats(answer_text(r))
    L = {}
    for b, f in FILES.items():
        for l in gzip.open(A.HERE / "inputs" / f, "rt"):
            r = json.loads(l)
            if r["mode"] == "J":
                L[r["aid"]] = len(answer_text(r).strip())
    pairs, res, trim = {}, {}, {}
    for (j, b), o in sorted(pool_sets().items()):
        if j in BIG:
            continue
        rows = [r for r in o["rows"] if r["aid"] in F]
        q = np.array([r["qid"] for r in rows])
        y = np.array([r["gold"] for r in rows], float)
        Z = demean(np.array([F[r["aid"]] for r in rows]), q)
        Z /= Z.std(0) + 1e-9
        d = demean(np.array([r["direct"] for r in rows]), q)
        yc = demean(y, q)
        uq = sorted(set(q))
        h1 = np.isin(q, list(np.random.default_rng(0).permutation(uq)[: len(uq) // 2]))
        surf, resid = np.zeros(len(rows)), np.zeros(len(rows))
        r2 = []
        for tr in (h1, ~h1):
            te = ~tr
            w, *_ = np.linalg.lstsq(Z[tr], yc[tr], rcond=None)
            surf[te] = Z[te] @ w
            u, *_ = np.linalg.lstsq(Z[tr], d[tr], rcond=None)
            resid[te] = d[te] - Z[te] @ u
            r2.append(1 - ((d[tr] - Z[tr] @ u) ** 2).sum() / (d[tr] ** 2).sum())
        for r, a, c in zip(rows, surf, resid):
            r["surface"], r["dir_resid"] = float(a), float(c)
        C = {m: perq_split(rows, m) for m in METH}
        qs = sorted(set.intersection(*[set(c) for c in C.values()]))
        pairs[(j, b)] = {m: (qs, np.array([C[m][x] for x in qs])) for m in C}
        tot = {m: np.array([C[m][x] for x in qs]).sum(0) for m in C}
        res[f"{j}|{b}"] = dict(r2_direct_on_surface=float(np.mean(r2)),
                               **{f"{m}|{part}": 100 * tot[m][2 * i] / tot[m][2 * i + 1] if tot[m][2 * i + 1] else None
                                  for m in C for i, part in enumerate(("all", "same", "diff"))})
        # format-trimmed pool: drop bare final answers (< 100 characters) and very long ones (> 8,000)
        keep = [r for r in o["rows"] if r["aid"] in L and 100 <= L[r["aid"]] <= 8000]
        C = {m: perq_split(keep, m) for m in ("verdict", "direct")}
        qs = sorted(set.intersection(*[set(c) for c in C.values()]))
        if b != "bbeh" and qs:
            trim[(j, b)] = {m: (qs, np.array([C[m][x] for x in qs])) for m in C}
    stats = {}
    for part, col in (("all", (0, 1)), ("same", (2, 3)), ("diff", (4, 5))):
        stats |= {f"{m}|gain|{part}": S.auc_gain(m, col=col) for m in METH[1:]}
        stats |= {f"{m}|level|{part}": S.level(m, col=col) for m in METH}
    est, draws = S.boot(pairs, stats)
    for part in ("all", "same", "diff"):
        est[f"resid_kept|{part}"] = S.ratio(draws, f"dir_resid|gain|{part}", f"direct|gain|{part}", est)
    tstats = {}
    for part, col in (("all", (0, 1)), ("same", (2, 3)), ("diff", (4, 5))):
        tstats |= {f"direct|gain|{part}": S.auc_gain("direct", col=col), f"verdict|level|{part}": S.level("verdict", col=col)}
    test, _ = S.boot(trim, tstats)
    full, _ = S.boot({p: v for p, v in pairs.items() if p in trim}, tstats)
    # how the pools make length and format informative (MATH and MMLU-Redux answer texts)
    fmt = {}
    for b in ("math", "mmlu"):
        rr = [json.loads(l) for l in gzip.open(A.HERE / "inputs" / FILES[b], "rt")]
        rr = [r for r in rr if r["mode"] == "J"]
        for src, tag in (("nemotron3-super-120b", "nemo"), ("qwen3.6-35b-a3b", "q36")):
            for gld in (0, 1):
                xs = [len(answer_text(r).strip()) for r in rr if r["src"] == src and r["gold"] == gld]
                fmt[f"{b}.{tag}.{gld}.bare"] = float(np.mean(np.array(xs) < 100))
                fmt[f"{b}.{tag}.{gld}.long"] = float(np.mean(np.array(xs) > 8000))
    # same-model, cannot-solve sets: does the verdict's ranking survive removing the surface features?
    from paper_data import sm_sets
    SF = {}
    for f in ("sm_mmlu", "sm_math", "sm2_mmlu", "sm2_math", "sm_bbeh"):
        for l in gzip.open(A.HERE / "inputs" / f"{f}_items.jsonl.gz", "rt"):
            r = json.loads(l)
            if r["mode"] == "J":
                SF[(f.startswith("sm2"), r["aid"])] = feats(answer_text(r))
    smp = defaultdict(dict)
    for (j, b, who), rows in sm_sets().items():
        if j in BIG or "strict" in who:
            continue
        sm2 = who == "olmo2-7b"
        rows = [dict(r) for r in rows if (sm2, r["aid"]) in SF]
        if len(rows) < 50:
            continue
        grp = np.array([f"{r['qid']}|{r['src']}" for r in rows])
        y = np.array([r["gold"] for r in rows], float)
        Z = demean(np.array([SF[(sm2, r["aid"])] for r in rows]), grp)
        Z /= Z.std(0) + 1e-9
        v, yc = demean(np.array([r["verdict"] for r in rows]), grp), demean(y, grp)
        q = np.array([r["qid"] for r in rows])
        uq = sorted(set(q))
        h1 = np.isin(q, list(np.random.default_rng(0).permutation(uq)[: len(uq) // 2]))
        vr, su = np.zeros(len(rows)), np.zeros(len(rows))
        for tr in (h1, ~h1):
            u, *_ = np.linalg.lstsq(Z[tr], v[tr], rcond=None)
            vr[~tr] = v[~tr] - Z[~tr] @ u
            w, *_ = np.linalg.lstsq(Z[tr], yc[tr], rcond=None)
            su[~tr] = Z[~tr] @ w
        for r, a, c in zip(rows, vr, su):
            r["verdict_resid"], r["surface"] = float(a), float(c)
        from paper_analysis import per_group
        C = {m: per_group(rows, m, lambda r: (r["qid"], r["src"])) for m in ("verdict", "verdict_resid", "surface")}
        qs = sorted(set.intersection(*[set(c) for c in C.values()]))
        smp[f"{b}|{who}"][(j, b)] = {m: (qs, np.array([C[m][x] for x in qs])) for m in C}
    sm_out = {}
    for key, prs in smp.items():
        e, _ = S.boot(prs, {m: S.level(m) for m in ("verdict", "verdict_resid", "surface")} |
                      {"resid_minus_verdict": S.auc_gain("verdict_resid")})
        sm_out[key] = e | {"k": len(prs)}
    out = dict(pairs=res, pooled=est, features=NAMES, format=fmt, sm=sm_out, trimmed=dict(trim=test, same_pairs_untrimmed=full,
               rule="answers of 100 to 8,000 characters; MMLU-Redux and MATH"))
    json.dump(out, open(A.HERE / "out_paper" / "surface_check.json", "w"), indent=1)
    for k, v in res.items():
        print(f"{k:22s} R2 {v['r2_direct_on_surface']:.2f} " + " ".join(
            f"{m[:4]} {v[m + '|all']:.1f}/{v[m + '|same'] or float('nan'):.1f}" for m in METH))
    print({k: (round(v["g"], 1), round(v["lo"], 1), round(v["hi"], 1)) for k, v in est.items()})
    print("sm", {k: {m: round(x["g"], 1) if isinstance(x, dict) else x for m, x in e.items()} for k, e in sm_out.items()})
    print("trimmed", {k: (round(v["g"], 1), round(v["lo"], 1), round(v["hi"], 1)) for k, v in test.items()})
    print("untrimmed", {k: (round(v["g"], 1), round(v["lo"], 1), round(v["hi"], 1)) for k, v in full.items()})


if __name__ == "__main__":
    main()
