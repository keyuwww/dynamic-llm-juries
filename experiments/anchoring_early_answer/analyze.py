"""Analyze the early-answering readouts: is own-answer anchoring already present before reasoning?

For every pool judgment by a Qwen judge we have the verdict the judge would give if stopped at
  A    (before writing anything), 25%, 50%, 75% of its reasoning, and C (its real verdict line).
"Accepts" = the CORRECT option beats INCORRECT (single answer) or the judge picks the response that
matches its own answer (pairwise).

The judge's own answer comes from a separate solve call (never shown to the judge).
  BBEH        exact match of committed final answers (same rule as the earlier BBEH analyses)
  RB2-Math    GLM-5.3-Flash decides SAME / DIFFERENT (tinker_jobs.py --phase match)
  JudgeBench  same, for each of the two responses; a pair counts only if exactly one response
              reaches the judge's own answer

  python3 experiments/anchoring_early_answer/analyze.py [--pilot] [--clean]   (--clean: clean_labels.py)
"""
import collections
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_pairwise_verdict, parse_verdict  # noqa: E402
from data import _extract_answer  # noqa: E402
sys.path.insert(0, str(HERE))
from clean_labels import same_value_items  # noqa: E402

CKPTS = ["A", "25", "50", "75", "C"]
OUT = HERE / ("out_pilot" if "--pilot" in sys.argv else "out")
CLEAN = "--clean" in sys.argv  # drop RB2-Math wrong answers that reach the right value; writes *_clean files
TAG = "_clean" if CLEAN else ""


def norm(ans):
    if not ans or ("The answer is" not in ans and "final answer is" not in ans):
        return None
    p = _extract_answer(ans.strip()).lower().replace(", ", ",").replace("**", "")
    p = p.split("\n")[0].strip()
    p = p[:-1] if p.endswith(".") else p
    if len(p) == 3 and p[0] == "(" and p[-1] == ")":
        p = p[1]
    return p or None


def letter(text):
    """JudgeBench multiple-choice answers end with the letter written five times (e.g. FFFFF)."""
    x = re.findall(r"\b([A-J])\1{4}\b", text or "")
    return x[-1] if x else None


def load(path):
    return [json.loads(l) for l in open(path)] if path.exists() else []


def boot_ci(x, n=2000, seed=0):
    x = np.asarray(x, float)
    if len(x) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    m = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


MAIN = ("rb2math", "judgebench", "bff")  # main set; BBEH (beyond the judges' ability) is reported separately


def _qkey(r):
    if r.get("q"):  # BFF: item ids are per conversation; cluster by question
        return (r["bench"], r["q"])
    return (r["bench"], r["item"].split("|")[0])


def _cluster_boot(R, f, n, seed=0):
    """Estimate and 95% interval, resampling whole questions (all candidates and judges of a question)."""
    groups = collections.defaultdict(list)
    for r in R:
        groups[_qkey(r)].append(r)
    keys = sorted(groups)
    rng = np.random.default_rng(seed)
    bs = [f([r for k in rng.integers(0, len(keys), len(keys)) for r in groups[keys[k]]]) for _ in range(n)]
    return f(R), np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5)


def _fe_effect(R, ck):
    """Linear probability model: accepts ~ own-answer match + judge FE + candidate FE.
    Only candidates that one Qwen matched and another did not identify the effect."""
    y = np.array([r[f"acc_{ck}"] for r in R], float)
    x = np.array([r["group"] == "match" for r in R], float)
    fes = [np.unique([f"{r['bench']}|{r['item']}" for r in R], return_inverse=True)[1],
           np.unique([f"{r['bench']}|{r['judge']}" for r in R], return_inverse=True)[1]]

    def demean(v):
        v = v.copy()
        for _ in range(50):
            for inv in fes:
                v = v - (np.bincount(inv, v) / np.bincount(inv))[inv]
        return v
    yd, xd = demean(y), demean(x)
    return (xd @ yd) / (xd @ xd) if xd @ xd > 1e-9 else float("nan")


def pooled_and_controlled(rows):
    L = ["\n## 5. Pooled over judges, with 95% intervals (questions resampled)\n",
         "Wrong candidates only. Gap = accept rate when the wrong answer matches the judge's own answer minus "
         "when it differs. Rescue gap = how much more often reasoning overturns an accept-at-A when the judge's "
         "own answer differs than when it matches.\n",
         "| Benchmark | Gap at A | Gap at C | Rescue gap |", "|---|---|---|---|"]
    W = [r for r in rows if r["target_ok"] == 0 and r["acc_A"] is not None and r["acc_C"] is not None]

    def gap(ck):
        return lambda R: (np.mean([r[f"acc_{ck}"] for r in R if r["group"] == "match"])
                          - np.mean([r[f"acc_{ck}"] for r in R if r["group"] == "differ"]))

    def rescue(R):
        return (np.mean([1 - r["acc_C"] for r in R if r["group"] == "differ" and r["acc_A"] == 1])
                - np.mean([1 - r["acc_C"] for r in R if r["group"] == "match" and r["acc_A"] == 1]))
    for b in ("main", "rb2math", "judgebench", "bff", "bbeh"):
        R = [r for r in W if r["bench"] in MAIN] if b == "main" else [r for r in W if r["bench"] == b]
        cells = [_cluster_boot(R, f, 2000) for f in (gap("A"), gap("C"), rescue)]
        L.append(f"| {b} | " + " | ".join(f"{e:+.2f} [{lo:+.2f}, {hi:+.2f}]" for e, lo, hi in cells) + " |")

    L += ["\n## 6. Control: the same wrong candidate, judged by Qwens whose own answers differ\n",
          "A wrong answer the judge also gave may just be a convincing wrong answer to everyone. This compares "
          "the three Qwens on the SAME wrong candidate (candidate fixed effects) and removes each judge's overall "
          "leniency (judge fixed effects). Single-answer benchmarks only (JudgeBench's groups are defined per "
          "pair, not per candidate).\n",
          "| Benchmark | Own-answer effect at A | at 50% | at C |", "|---|---|---|---|"]
    S = [r for r in W if r["bench"] != "judgebench" and r["acc_50"] is not None]
    for b in ("main", "rb2math", "bff", "bbeh"):
        R = [r for r in S if r["bench"] in MAIN] if b == "main" else [r for r in S if r["bench"] == b]
        cells = [_cluster_boot(R, lambda X, ck=ck: _fe_effect(X, ck), 500) for ck in ("A", "50", "C")]
        L.append(f"| {b} | " + " | ".join(f"{e:+.3f} [{lo:+.3f}, {hi:+.3f}]" for e, lo, hi in cells) + " |")
    return L


def main():
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, f)}
    reads = collections.defaultdict(dict)
    meta = {}
    for r in load(OUT / "readouts.jsonl"):
        reads[(r["judge"], r["item_id"])][r["ckpt"]] = r["margin"]
        meta[(r["judge"], r["item_id"])] = (r["n_prompt"], r["pool_n_in"])
    matches = {r["cache_key"]: r["verdict"] for r in load(OUT / "matches_glm5.3-flash.jsonl")}
    solves = {r["cache_key"]: r for r in load(OUT / "solves.jsonl")}

    # Reruns of cut-off outputs (tinker_jobs.py --phase extend: same prompt, from scratch, 64K budget).
    # They replace the judge's OWN answer and the judge's transcript; candidates stay exactly as the judge saw them.
    ext = {}
    for f in sorted(OUT.glob("extended*.jsonl")):
        ext.update({r["cache_key"]: r for r in load(f)})
    matches.update({r["cache_key"]: r["verdict"] for r in load(OUT / "matches_glm5.3-flash_ext.jsonl")})
    for k, r in solves.items():
        if f"solve|{k}" in ext:
            solves[k] = dict(r, answer=ext[f"solve|{k}"]["text"])
    ext_reads = collections.defaultdict(dict)
    for r in load(OUT / "readouts_ext.jsonl"):
        ext_reads[(r["judge"], r["item_id"])][r["ckpt"]] = r["margin"]
    for key, ck in ext_reads.items():
        reads[key] = ck  # the whole set of checkpoints comes from the finished transcript
        jobs[key] = dict(jobs[key], transcript=ext[f"judge|{key[0]}|{key[1]}"]["text"])

    ans_bbeh = {}  # every pool model's answer, as the judges saw it (candidates)
    for line in open(HERE.parent / "tinker_pool" / "bbeh_results" / "answers.jsonl"):
        r = json.loads(line)
        ans_bbeh[(r["model"], r["item"])] = norm(r["answer"])
    own_bbeh = dict(ans_bbeh)  # the judge's own answer: the finished rerun where the pool answer was cut off
    for k, r in ext.items():
        kind, model, q = k.split("|", 2)
        if kind == "solve" and r.get("bench") == "bbeh":
            own_bbeh[(model, q)] = norm(r["text"])

    rows = []
    for key, ck in reads.items():
        j = jobs[key]
        judge, iid = key
        spoken = (parse_pairwise_verdict if j["pairwise"] else parse_verdict)(j["transcript"])
        if j["bench"] == "bbeh":
            qid, exam = iid.split("|")
            if exam == judge:
                continue  # judging its own answer: trivially the same text
            own, cand = own_bbeh.get((judge, qid)), ans_bbeh.get((exam, qid))
            if own is None or cand is None:
                continue
            group = "match" if own == cand else "differ"
            target_ok, sign = j["gold"], 1
        elif j["bench"] in ("rb2math", "bff"):
            v = matches.get(f"{judge}|{iid}|0")
            if v not in ("SAME", "DIFFERENT"):
                continue
            group = "match" if v == "SAME" else "differ"
            target_ok, sign = j["gold"], 1
        else:  # judgebench (pairwise)
            own_l = letter(solves.get(f"{judge}|{j['qid']}", {}).get("answer"))
            vs = []
            for ci, cand in enumerate(j["candidates"]):
                cl = letter(cand)
                if own_l and cl:  # both give a 5x-letter answer: match exactly (GLM agrees 99.2%)
                    vs.append("SAME" if own_l == cl else "DIFFERENT")
                else:
                    vs.append(matches.get(f"{judge}|{iid}|{ci}"))
            if None in vs or "NONE" in vs or vs.count("SAME") == 2:
                continue
            if vs.count("SAME") == 1:  # target = the response that reaches the judge's own answer
                tgt_a = vs[0] == "SAME"
                group = "match"
            else:  # neither reaches it: target = the wrong response, as the no-anchor baseline
                tgt_a = j["gold"] == 0
                group = "differ"
            sign = 1 if tgt_a else -1
            target_ok = int(j["gold"] == (1 if tgt_a else 0))
        acc = {c: int(sign * ck[c] > 0) for c in CKPTS if c in ck}
        if spoken is not None:
            spoken = int(spoken == 1) if sign == 1 else int(spoken == 0)
        rows.append(dict(bench=j["bench"], judge=judge, item=iid, group=group, target_ok=target_ok, q=j.get("uid"),
                         spoken=spoken, **{f"acc_{c}": acc.get(c) for c in CKPTS},
                         **{f"m_{c}": (sign * ck[c] if c in ck else None) for c in CKPTS}))

    if CLEAN:  # RB2-Math "wrong" answers that reach the right value are not wrong (clean_labels.py)
        bad = same_value_items()
        rows = [r for r in rows if not (r["target_ok"] == 0 and r["item"] in bad)]

    L = ["# Early answering: is own-answer anchoring already there before the judge reasons?\n",
         f"Source: `{OUT.name}/`, answer matcher: GLM-5.3-Flash. Judges: the three Qwen models of the Tinker pool, thinking off, their own "
         "pool transcripts. Each judgment is read at A (before any reasoning), 25/50/75% of the reasoning, "
         "and C (the real verdict line), by appending `VERDICT:` and comparing the log-probabilities of the "
         "two verdict words.\n"]

    # sanity checks
    n_tok_ok = sum(1 for (a, b) in meta.values() if a == b)
    agree = [r["acc_C"] == r["spoken"] for r in rows if r["acc_C"] is not None and r["spoken"] is not None]
    L.append(f"Checks: rebuilt prompt length equals the pool's in {n_tok_ok}/{len(meta)} judgments; "
             f"the C readout equals the parsed spoken verdict in {np.mean(agree):.3f} of {len(agree)}.\n")

    L.append("## 1. Wrong candidates: how often the judge accepts, by checkpoint\n")
    L.append("Single-answer benchmarks: *match* = the wrong answer equals the judge's own (wrong) answer; "
             "*differ* = the judge's own answer was something else. JudgeBench (pairwise): *match* = exactly one "
             "response reaches the judge's own answer and it is the wrong one; *differ* = neither response reaches "
             "it; 'accepts' = the judge picks the wrong response.\n")
    L.append("| Benchmark | Judge | Group | n | A | 25% | 50% | 75% | C |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for (b, jg) in sorted({(r["bench"], r["judge"]) for r in rows}):
        for g in ("match", "differ"):
            R = [r for r in rows if r["bench"] == b and r["judge"] == jg and r["group"] == g and r["target_ok"] == 0]
            if not R:
                continue
            cells = []
            for c in CKPTS:
                v = [r[f"acc_{c}"] for r in R if r[f"acc_{c}"] is not None]
                cells.append(f"{np.mean(v):.2f}" if v else "–")
            L.append(f"| {b} | {jg} | {g} | {len(R)} | " + " | ".join(cells) + " |")

    L.append("\n## 2. The errors: was the judge already accepting at A?\n")
    L.append("Errors = wrong candidates the judge accepts at C. 'Already at A' = it also accepted at A, "
             "before writing any reasoning.\n")
    L.append("| Benchmark | Judge | Anchoring errors (match) | already at A | Other errors (differ) | already at A |")
    L.append("|---|---|---|---|---|---|")
    pooled = {"match": [], "differ": []}
    for (b, jg) in sorted({(r["bench"], r["judge"]) for r in rows}):
        cells = []
        for g in ("match", "differ"):
            E = [r for r in rows if r["bench"] == b and r["judge"] == jg and r["group"] == g
                 and r["target_ok"] == 0 and r["acc_C"] == 1 and r["acc_A"] is not None]
            pooled[g] += [r["acc_A"] for r in E]
            cells += [str(len(E)), f"{np.mean([r['acc_A'] for r in E]):.2f}" if E else "–"]
        L.append(f"| {b} | {jg} | " + " | ".join(cells) + " |")

    L.append("\n## 3. Does reasoning rescue the judge? (wrong candidates that were accepted at A)\n")
    L.append("Share that the judge rejects by C, after accepting at A.\n")
    L.append("| Benchmark | Judge | match: n | match: rescued | differ: n | differ: rescued |")
    L.append("|---|---|---|---|---|---|")
    for (b, jg) in sorted({(r["bench"], r["judge"]) for r in rows}):
        cells = []
        for g in ("match", "differ"):
            R = [r for r in rows if r["bench"] == b and r["judge"] == jg and r["group"] == g
                 and r["target_ok"] == 0 and r["acc_A"] == 1 and r["acc_C"] is not None]
            cells += [str(len(R)), f"{np.mean([1 - r['acc_C'] for r in R]):.2f}" if R else "–"]
        L.append(f"| {b} | {jg} | " + " | ".join(cells) + " |")

    L.append("\n## 4. Same for correct candidates (control)\n")
    L.append("| Benchmark | Judge | Group | n | accepts at A | accepts at C |")
    L.append("|---|---|---|---|---|---|")
    for (b, jg) in sorted({(r["bench"], r["judge"]) for r in rows}):
        for g in ("match", "differ"):
            R = [r for r in rows if r["bench"] == b and r["judge"] == jg and r["group"] == g and r["target_ok"] == 1
                 and r["acc_A"] is not None and r["acc_C"] is not None]
            if R:
                L.append(f"| {b} | {jg} | {g} | {len(R)} | {np.mean([r['acc_A'] for r in R]):.2f} | "
                         f"{np.mean([r['acc_C'] for r in R]):.2f} |")

    L += pooled_and_controlled(rows)
    (OUT / f"rows{TAG}.json").write_text(json.dumps(rows))
    text = "\n".join(L) + "\n"
    (OUT / f"results{TAG}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
