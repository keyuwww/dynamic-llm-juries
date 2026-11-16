"""Push while solving: does pushing the belief direction while Qwen3.5-9B SOLVES an RB2 Math question (no candidate in
the prompt) change what it believes? Reads cannon_belief/out_solve_steer/<cond>.jsonl (7 answers per question per
condition; <cond>_redo.jsonl replaces answers that hit the 8192-token cap) and scores each candidate's belief = share of
the 7 answers that reach the candidate's answer.

Matching, no new GLM calls: a new answer whose normalised \\boxed{} equals the boxed answer of one of the judge's original
7 solves inherits that solve's GLM-5.3-Flash verdict against each candidate (majority if several). New answers with no
such twin are matched by GLM directly: --glm-jobs writes them to inputs/pairs_solvesteer.jsonl.gz (one per distinct
boxed answer and candidate), then
  .venv/bin/modal run experiments/anchoring_early_answer/modal_app.py --phase pairs --pairs solvesteer

  python3 experiments/anchoring_early_answer/solve_steer_analysis.py [--glm-jobs]
"""
import argparse
import collections
import gzip
import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / "cannon_belief" / "out_solve_steer"
OUT = HERE / "out"
JUDGE = "qwen3.5-9b"
CONDS = [("none", "no push"), ("belief_-6", "belief −6 sd"), ("belief_6", "belief +6 sd"), ("random_-6", "random −6 sd")]


def boxed(t):
    i = t.rfind("\\boxed{")
    if i < 0:
        return None
    j, d, s = i + 7, 1, i + 7
    while j < len(t) and d:
        d += t[j] == "{"
        d -= t[j] == "}"
        j += 1
    return t[s:j - 1]


def norm(b):
    if b is None:
        return None
    b = re.sub(r"\\(text|mathrm|textbf|mbox)\{([^}]*)\}", r"\2", b)
    for x, y in (("\\dfrac", "\\frac"), ("\\tfrac", "\\frac"), ("\\left", ""), ("\\right", ""), ("\\,", ""),
                 ("\\!", ""), ("$", "")):
        b = b.replace(x, y)
    return re.sub(r"\s+", "", b).rstrip(".").lower() or None


def jl(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def boot(qs, f, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    u = sorted(set(qs))
    return np.percentile([f(rng.choice(u, len(u))) for _ in range(n)], [2.5, 97.5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glm-jobs", action="store_true")
    a = ap.parse_args()
    # candidates: RB2 Math items judged by Qwen3.5-9B, with correctness and original belief
    rows = {r["item"]: r for r in json.load(open(OUT / "belief_rows.json")) if r["judge"] == JUDGE
            and r["bench"] == "rb2math"}
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        cands, ctext = collections.defaultdict(list), {}
        for j in map(json.loads, f):
            if j["judge"] == JUDGE and j["bench"] == "rb2math" and j["item_id"] in rows:
                cands[j["qid"]].append(j["item_id"])
                ctext[j["item_id"]] = (j["question"], j["candidates"][0])
    # original solves -> normalised boxed answer; their GLM verdicts against each candidate
    orig = {}
    for s in jl(OUT / "solves_k.jsonl") + jl(OUT / "solves_k_rerun.jsonl"):
        if s["model"] == JUDGE and s["qid"] in cands:
            orig[(s["qid"], int(s["sample"]))] = norm(boxed(s["answer"]))
    glm = {r["cache_key"]: r["verdict"] for p in ("matches_glm5.3-flash_k.jsonl", "matches_glm5.3-flash_k_rerun.jsonl")
           for r in jl(OUT / p)}
    key = collections.defaultdict(collections.Counter)  # (item, boxed) -> GLM votes of original solves with that boxed
    for (q, s), b in orig.items():
        for it in cands[q]:
            v = glm.get(f"{JUDGE}|{it}|0|s{s}")
            if b and v in ("SAME", "DIFFERENT"):
                key[(it, b)][v] += 1
    # direct GLM matches of new answers (solve_steer_analysis.py --glm-jobs, then tinker_jobs.py --phase pairs)
    new = {r["cache_key"]: r["verdict"] for r in jl(OUT / "matches_glm5.3-flash_solvesteer.jsonl")}

    res, pending = {}, {}
    for cond, _ in CONDS:
        ans = {(r["qid"], r["sample"]): r for r in jl(SRC / f"{cond}.jsonl")}
        ans.update({(r["qid"], r["sample"]): r for r in jl(SRC / f"{cond}_redo.jsonl")})
        per = collections.defaultdict(dict)  # item -> sample -> 0/1
        n_cut = n_reuse = n_glm = n_miss = 0
        for (q, s), r in ans.items():
            if q not in cands:
                continue
            if not r["clean"]:
                n_cut += 1
                continue
            b = norm(r["boxed"])
            src = set()
            for it in cands[q]:
                c = key.get((it, b)) if b else None
                if c:
                    per[it][s] = int(c["SAME"] > c["DIFFERENT"])
                    src.add("reuse")
                    continue
                k = f"{it}|b:{b}" if b else f"{it}|{cond}|s{s}"  # one GLM call per distinct boxed answer
                if k in new and new[k] is not None:
                    per[it][s] = int(new[k] == "SAME")  # NONE (no final answer) does not reach the candidate
                    src.add("glm")
                else:
                    pending[k] = dict(cache_key=k, question=ctext[it][0], a=r["text"], b=ctext[it][1])
                    src.add("miss")
            n_reuse += src == {"reuse"}
            n_glm += "glm" in src and "miss" not in src
            n_miss += "miss" in src
        res[cond] = dict(belief={it: np.mean(list(v.values())) for it, v in per.items() if len(v) >= 3},
                         n=len(ans), cut=n_cut, reuse=n_reuse, glm=n_glm, miss=n_miss,
                         mean_len=np.mean([r["n_out"] for r in ans.values()]))

    L = ["# Push while solving (Qwen3.5-9B, RB2 Math)\n",
         "The belief direction (held-out half, layers 14–26) is pushed while the judge solves the question with no "
         "candidate shown; 7 answers per question at T = 0.7. Belief in a candidate = share of those answers that reach "
         "the candidate's answer (GLM-5.3-Flash). A new answer with the same boxed answer as one of the judge's original "
         "solves reuses that solve's GLM verdict; the rest are matched by GLM directly. Answers still unmatched or cut "
         "off are left out. Changes are against the no-push run; 95% intervals resample questions.\n",
         "| condition | answers | still cut off | reused match | new GLM match | unmatched | mean length (tokens) |",
         "|---|---|---|---|---|---|---|"]
    for cond, lab in CONDS:
        r = res[cond]
        L.append(f"| {lab} | {r['n']} | {r['cut']} | {r['reuse']} | {r['glm']} | {r['miss']} | {r['mean_len']:.0f} |")
    base = res["none"]["belief"]
    groups = [("wrong, originally believed (≥ 1/7)", lambda r: not r["target_ok"] and r["belief"] > 0),
              ("wrong, never reached", lambda r: not r["target_ok"] and r["belief"] == 0),
              ("correct", lambda r: r["target_ok"])]
    L += ["", "Mean belief (share of the 7 answers reaching the candidate), and change vs no push:\n",
          "| condition | " + " | ".join(g for g, _ in groups) + " |", "|---|" + "---|" * len(groups)]
    for cond, lab in CONDS:
        cells = []
        for _, m in groups:
            its = [it for it in res[cond]["belief"] if it in base and m(rows[it])]
            qof = {it: it.rsplit("-", 1)[0] for it in its}
            bq = collections.defaultdict(list)
            for it in its:
                bq[qof[it]].append(it)
            mean = np.mean([res[cond]["belief"][it] for it in its])
            if cond == "none":
                cells.append(f"{100 * mean:.0f}% (n={len(its)})")
                continue
            d = lambda qs: np.mean([res[cond]["belief"][it] - base[it] for q in qs for it in bq[q]])
            lo, hi = boot(list(bq), d)
            cells.append(f"{100 * mean:.0f}% ({100 * d(list(bq)):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}])")
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    # sanity: the no-push rerun should reproduce the original belief
    its = [it for it in base]
    L.append(f"\nSanity check: no-push belief vs the original 7 solves, correlation "
             f"{np.corrcoef([base[i] for i in its], [rows[i]['belief'] for i in its])[0, 1]:.2f} over {len(its)} "
             f"candidates.")
    (OUT / "solve_steer.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\n{len(pending)} (answer, candidate) pairs still need a GLM match")
    if a.glm_jobs:
        with gzip.open(HERE / "inputs" / "pairs_solvesteer.jsonl.gz", "wt") as f:
            f.write("".join(json.dumps(p) + "\n" for p in pending.values()))
        print("wrote inputs/pairs_solvesteer.jsonl.gz")


if __name__ == "__main__":
    main()
