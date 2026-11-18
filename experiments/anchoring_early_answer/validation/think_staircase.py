"""Thinking-on belief staircase on audited labels (Nov 17).

The three Qwens judged the main set with thinking ON (Experiment 5, out/think_gen.jsonl; ~630 cut-off outputs were
regenerated from scratch in out/think_gen_rerun.jsonl, which replaces the cut-off version). Verdict = the spoken
verdict after </think>. Belief = the same thinking-off belief as everywhere else (7 own answers, belief_rows_clean.json),
so the only thing that changes between the two staircases is whether the judge thinks while grading.

Labels: RB2 Math keeps its value-match cleaning; BFF / JudgeBench keep only GLM-5.3 'LABEL_OK' answers (as in
clean_staircase.py). Judgments that never close </think> or have no verdict are counted and left out.

  python3 experiments/anchoring_early_answer/validation/think_staircase.py  -> validation/think_staircase.md
"""
import collections
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_pairwise_verdict, parse_verdict  # noqa: E402

V = HERE / "validation"
JUDGES = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]
BINS = ["0/7", "1-3", "4-6", "7/7"]


def load_think():
    """(judge, item) -> verdict (1/0) or a failure reason string."""
    out = {}
    for f in ("think_gen.jsonl", "think_gen_rerun.jsonl"):  # rerun read second: replaces the cut-off version
        for line in open(HERE / "out" / f):
            if '"key": "judge|' not in line[:400] and '"key":"judge|' not in line[:400]:
                continue
            r = json.loads(line)
            kind, bench, iid = r["key"].split("|", 2)
            if kind != "judge" or r["judge"] not in JUDGES:
                continue
            if "</think>" not in r["text"]:
                out[(r["judge"], iid)] = "cut"
                continue
            after = r["text"].split("</think>", 1)[1]
            v = (parse_pairwise_verdict if bench == "judgebench" else parse_verdict)(after)
            out[(r["judge"], iid)] = "noverdict" if v is None else int(v)  # judgebench: 1 = A preferred
    return out


def jb_sign():
    """JudgeBench rows: +1 if the row's target is response A, -1 if B (recovered from the thinking-off readout: the row
    stores sign * margin at C, the readout file the raw margin)."""
    raw = collections.defaultdict(dict)
    for f in ("readouts.jsonl", "readouts_ext.jsonl"):
        ext = collections.defaultdict(dict)
        for line in open(HERE / "out" / f):
            r = json.loads(line)
            if r["bench"] == "judgebench" if "bench" in r else "judgebench" in r["item_id"]:
                ext[(r["judge"], r["item_id"])][r["ckpt"]] = r["margin"]
        raw.update(ext)
    return raw


def binof(r):
    k = round(float(r["belief"]) * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def stair(S, key):
    return [np.mean([r[key] for r in S if r["b"] == b]) if any(r["b"] == b for r in S) else np.nan for b in BINS]


QID = None


def qid_of(r):
    """Judge-independent question id (the cluster for every interval in the paper)."""
    global QID
    if QID is None:
        import gzip
        QID = {}
        for sfx in ("", "_nemotron", "_deepseek", "_kimi", "_nano"):
            for j in map(json.loads, gzip.open(HERE / "inputs" / f"readout_jobs{sfx}.jsonl.gz", "rt")):
                QID[j["item_id"]] = f"{j['bench']}|{j['qid']}"
    return QID.get(r["item"], r["item"])


def boot(S, key, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    by = collections.defaultdict(list)
    for r in S:
        by[qid_of(r)].append(r)
    items = list(by)
    g = []
    for _ in range(n):
        smp = [r for i in rng.choice(len(items), len(items)) for r in by[items[i]]]
        s = stair(smp, key)
        g.append(s[3] - s[0])
    return np.nanpercentile(g, [2.5, 97.5])


def boot_diff(S, n=2000, seed=0):
    """Interval for (thinking-on gap) - (thinking-off gap) on the same answers."""
    rng = np.random.default_rng(seed)
    by = collections.defaultdict(list)
    for r in S:
        by[qid_of(r)].append(r)
    items = list(by)
    d = []
    for _ in range(n):
        smp = [r for i in rng.choice(len(items), len(items)) for r in by[items[i]]]
        on, off = stair(smp, "on"), stair(smp, "off")
        d.append((on[3] - on[0]) - (off[3] - off[0]))
    return np.nanpercentile(d, [2.5, 97.5])


def main():
    glm = {}
    for f in ("ask_glm5.3_labelaudit.jsonl", "ask_glm5.3_labelauditrb2.jsonl"):  # BFF+JB, RB2 Math (Nov 18)
        for line in open(HERE / "out" / f):
            r = json.loads(line)
            m = re.findall(r"AUDIT:\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", r["text"])
            glm[r["cache_key"].split("|", 2)[2]] = m[-1] if m else None
    think = load_think()
    raw = jb_sign()
    rows = [r for r in json.load(open(HERE / "out" / "belief_rows_clean.json"))
            if r["judge"] in JUDGES and int(r["target_ok"]) == 0]
    clean = [r for r in rows if glm.get(r["item"]) == "LABEL_OK"]
    fail = collections.Counter()
    W = []
    for r in clean:
        t = think.get((r["judge"], r["item"]))
        if t is None:
            fail["no thinking-on judgment"] += 1
            continue
        if isinstance(t, str):
            fail[t] += 1
            continue
        if r["spoken"] in (None, "None"):
            fail["no thinking-off verdict"] += 1
            continue
        if r["bench"] == "judgebench":
            m = raw.get((r["judge"], r["item"]), {}).get("C")
            if not m or r["m_C"] is None:
                fail["judgebench sign unknown"] += 1
                continue
            t = t if r["m_C"] / m > 0 else 1 - t  # approval of the target = picking it
        W.append(dict(r, b=binof(r), on=t, off=int(r["spoken"])))
    L = ["# Belief staircase with thinking ON vs OFF (three Qwens, audited labels)\n",
         "Wrong answers approved, by belief (how often the judge reaches that answer in 7 thinking-off solves). Same "
         "answers in both rows: only those with a thinking-on verdict and a thinking-off verdict. Gap = 7/7 minus 0/7, "
         "95% interval resampling answers.\n",
         f"Audited wrong answers × judges: {len(clean)}; used {len(W)}; left out: "
         + ", ".join(f"{k} {v}" for k, v in fail.most_common()) + ".\n",
         "| judge | grading | " + " | ".join(BINS) + " | gap 7/7 − 0/7 |", "|---|---|---|---|---|---|---|"]
    for name, js in [("3 Qwens pooled", JUDGES)] + [(j, [j]) for j in JUDGES]:
        S = [r for r in W if r["judge"] in js]
        for lab, key in (("thinking off", "off"), ("thinking on", "on")):
            s = stair(S, key)
            lo, hi = boot(S, key)
            L.append(f"| {name} | {lab} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})"
                                                         for v, b in zip(s, BINS))
                     + f" | {100 * (s[3] - s[0]):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}] |")
    lo, hi = boot_diff(W)
    on, off = stair(W, "on"), stair(W, "off")
    L += ["", f"Thinking on minus thinking off, pooled gap: {100 * ((on[3] - on[0]) - (off[3] - off[0])):+.0f} "
              f"[{100 * lo:+.0f}, {100 * hi:+.0f}] points.", ""]
    L += ["## By benchmark (pooled Qwens, thinking on)\n", "| bench | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
    for bench in ["rb2math", "judgebench", "bff"]:
        S = [r for r in W if r["bench"] == bench]
        L.append(f"| {bench} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})"
                                              for v, b in zip(stair(S, "on"), BINS)) + " |")
    # right answers: does thinking also make the judge stricter on right answers it doesn't believe?
    R = []
    for r in json.load(open(HERE / "out" / "belief_rows_clean.json")):
        if r["judge"] in JUDGES and int(r["target_ok"]) == 1 and r["spoken"] not in (None, "None"):
            t = think.get((r["judge"], r["item"]))
            if isinstance(t, int) and r["bench"] == "judgebench":
                m = raw.get((r["judge"], r["item"]), {}).get("C")
                t = None if not m or r["m_C"] is None else (t if r["m_C"] / m > 0 else 1 - t)
            if isinstance(t, int):
                R.append(dict(r, b=binof(r), on=t, off=int(r["spoken"])))
    L += ["", "## Right answers approved (pooled Qwens)\n", "| grading | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
    for lab, key in (("thinking off", "off"), ("thinking on", "on")):
        L.append(f"| {lab} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in R)})"
                                            for v, b in zip(stair(R, key), BINS)) + " |")
    (V / "think_staircase.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
