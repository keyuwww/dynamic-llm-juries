"""Does an expert reference answer remove the strong-belief errors? (Nov 16)

Three Qwens, thinking off, BFF-Bench (459 answers with a unanimous expert label). Same judge prompt as the main
runs, plus BFF-Bench's own expert-written reference answer for that question (the No Free Labels setting). Belief
scores come from the existing 7-answer runs (belief_rows_clean.json); the usual verdict is the spoken verdict from the
main runs, so every item is compared with itself (paired).

  python3 experiments/anchoring_early_answer/reference_test.py --prep   -> inputs/gen_bffref.jsonl.gz
  (modal_app.py::run --phase gen --pairs bffref; then modal volume get ... gen_bffref.jsonl out/)
  python3 experiments/anchoring_early_answer/reference_test.py          -> out/reference_test.md
"""
import collections
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from common import parse_verdict  # noqa: E402

QWENS = ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]
ANCHOR = "Is the assistant's FINAL response a correct answer"
REF = ("[EXPERT REFERENCE ANSWER]\n{ref}\n[END OF EXPERT REFERENCE ANSWER]\n\n"
       "An expert-written reference answer to the user's final question is given above; use it as the ground truth "
       "for what the correct answer is.\n\n")
BINS = ("0/7", "1-3", "4-6", "7/7")


def binof(b):
    k = round(b * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"


def load():
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {(j["judge"], j["item_id"]): j for j in map(json.loads, f) if j["bench"] == "bff" and j["judge"] in QWENS}
    refs = {it["id"]: it["ref"] for it in map(json.loads, open(HERE.parent / "beyond_capability" / "inputs" / "bff_items.jsonl"))}
    rows = {(r["judge"], r["item"]): r for r in json.load(open(HERE / "out" / "belief_rows_clean.json"))
            if r["bench"] == "bff" and r["judge"] in QWENS}
    return jobs, refs, rows


def refkey(j):  # BFF uid + turn from the qid suffix ("bff-<key>-t2" -> "<uid>|2")
    return f"{j['uid']}|{j['qid'].rsplit('-t', 1)[1]}"


def prep():
    jobs, refs, rows = load()
    out = []
    for (judge, iid) in rows:
        j = jobs[(judge, iid)]
        ref = refs.get(iid)
        msg = j["messages"][0]["content"]
        assert ANCHOR in msg
        if not ref:  # 3 BFF items (9 rows) have no expert reference in the release; skipped
            continue
        out.append(dict(cache_key=f"bffref|{judge}|{iid}", model=judge,
                        messages=[{"role": "user", "content": msg.replace(ANCHOR, REF.format(ref=ref) + ANCHOR, 1)}]))
    with gzip.open(HERE / "inputs" / "gen_bffref.jsonl.gz", "wt") as f:
        f.write("".join(json.dumps(x) + "\n" for x in out))
    print(len(out), collections.Counter(x["model"] for x in out))


KREF = ("[REFERENCE ANSWER FROM A STRONG AI MODEL]\n{ref}\n[END OF REFERENCE ANSWER]\n\n"
        "A reference answer to the user's final question, written by a strong AI model, is given above; use it as the "
        "reference for what the correct answer is.\n\n")


def kimi_refs():
    """BFF question key 'uid|turn' -> Kimi-K3.1-Pro's own answer (Nov 8-9 runs; 141/160 agree with the expert)."""
    L = map(json.loads, open(HERE.parent / "beyond_capability" / "out" / "bff_solves_kimi-k3.1-pro.jsonl"))
    return {x["qid"]: x["samples"][0]["text"] for x in L if x["samples"] and x["samples"][0]["clean"]}


def prep_kimi():
    jobs, refs, rows = load()
    kr = kimi_refs()
    out = []
    for (judge, iid) in rows:
        j = jobs[(judge, iid)]
        if not refs.get(iid):  # same 1,295 items as the expert-reference run
            continue
        k = kr.get(f"{j['uid']}|{j['qid'].rsplit('-t', 1)[1]}")
        if not k:
            continue
        msg = j["messages"][0]["content"].replace(ANCHOR, KREF.format(ref=k) + ANCHOR, 1)
        out.append(dict(cache_key=f"bffkimi|{judge}|{iid}", model=judge, messages=[{"role": "user", "content": msg}]))
    with gzip.open(HERE / "inputs" / "gen_bffkimi.jsonl.gz", "wt") as f:
        f.write("".join(json.dumps(x) + "\n" for x in out))
    print(len(out), collections.Counter(x["model"] for x in out))


def prep_both():
    """Commit first AND the expert reference: own earlier solve as an assistant turn, then the reference judge prompt."""
    jobs, refs, rows = load()
    solve_msgs = {(j["model"], j["qid"]): j["messages"] for j in map(json.loads, open(HERE / "inputs" / "solve_jobs.jsonl"))}
    own = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / "solves.jsonl"))}
    first = "Now grade another AI assistant's answer to the same question.\n\n"
    out = []
    for (judge, iid) in rows:
        j = jobs[(judge, iid)]
        ref, o = refs.get(iid), own.get(f"{judge}|{j['qid']}")
        if not ref or not o or not o["clean"]:
            continue
        msg = j["messages"][0]["content"].replace(ANCHOR, REF.format(ref=ref) + ANCHOR, 1)
        out.append(dict(cache_key=f"bffrefcf|{judge}|{iid}", model=judge, messages=solve_msgs[(judge, j["qid"])] + [
            {"role": "assistant", "content": o["answer"]}, {"role": "user", "content": first + msg}]))
    with gzip.open(HERE / "inputs" / "gen_bffrefcf.jsonl.gz", "wt") as f:
        f.write("".join(json.dumps(x) + "\n" for x in out))
    print(len(out), collections.Counter(x["model"] for x in out))


def boot(pairs, stat, n=2000, seed=0):
    """pairs: list of (qid, usual, ref, ok). Cluster bootstrap over questions."""
    rng = np.random.default_rng(seed)
    by = collections.defaultdict(list)
    for p in pairs:
        by[p[0]].append(p)
    keys = list(by)
    est = stat(pairs)
    sims = []
    for _ in range(n):
        s = [p for k in rng.choice(keys, len(keys)) for p in by[k]]
        v = stat(s)
        if v is not None:
            sims.append(v)
    return est, np.percentile(sims, 2.5), np.percentile(sims, 97.5)


def bal(pairs, idx):
    pos = [p[idx] for p in pairs if p[3] == 1]
    neg = [1 - p[idx] for p in pairs if p[3] == 0]
    return None if not pos or not neg else 100 * (np.mean(pos) + np.mean(neg)) / 2


def analyze():
    jobs, _, rows = load()
    gen = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / "gen_bffref.jsonl"))}
    P = []  # (qid, usual, ref, ok, judge, bin)
    for (judge, iid), r in rows.items():
        g = gen.get(f"bffref|{judge}|{iid}")
        v = parse_verdict(g["text"]) if g else None
        if v is None or r.get("spoken") is None:
            continue
        P.append((jobs[(judge, iid)]["qid"], int(r["spoken"]), int(v), int(r["target_ok"]), judge, binof(r["belief"])))
    L = ["# Expert reference answer vs strong-belief errors (BFF-Bench, three Qwens, thinking off)\n",
         f"{len(P)} paired judgments (same item, usual prompt vs + expert reference). 95% intervals resample questions.\n",
         "## Wrong answers approved, by belief\n", "| condition | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
    for name, idx in (("usual judge prompt", 1), ("+ expert reference answer", 2)):
        cells = []
        for b in BINS:
            v = [p[idx] for p in P if p[3] == 0 and p[5] == b]
            cells.append(f"{100 * np.mean(v):.0f}% (n={len(v)})" if v else "–")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    L += ["", "| change (points) | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
    cells = []
    for b in BINS:
        sub = [p for p in P if p[3] == 0 and p[5] == b]
        if sub:
            e, lo, hi = boot(sub, lambda s: 100 * (np.mean([p[2] for p in s]) - np.mean([p[1] for p in s])) if s else None)
            cells.append(f"{e:+.0f} [{lo:+.0f}, {hi:+.0f}]")
        else:
            cells.append("–")
    L.append("| wrong answers | " + " | ".join(cells) + " |")
    L += ["", "## Right answers approved, by belief\n", "| condition | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
    for name, idx in (("usual judge prompt", 1), ("+ expert reference answer", 2)):
        cells = []
        for b in BINS:
            v = [p[idx] for p in P if p[3] == 1 and p[5] == b]
            cells.append(f"{100 * np.mean(v):.0f}% (n={len(v)})" if v else "–")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    L += ["", "## Balanced accuracy\n", "| judge | usual | + reference | change |", "|---|---|---|---|"]
    for j in QWENS + ["all three"]:
        sub = [p for p in P if j == "all three" or p[4] == j]
        e1, e2 = bal(sub, 1), bal(sub, 2)
        d = boot(sub, lambda s: (bal(s, 2) - bal(s, 1)) if bal(s, 1) is not None and bal(s, 2) is not None else None)
        L.append(f"| {j} | {e1:.1f}% | {e2:.1f}% | {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}] |")
    strong = [p for p in P if p[3] == 0 and p[5] in ("4-6", "7/7")]
    e = boot(strong, lambda s: 100 * (np.mean([p[2] for p in s]) - np.mean([p[1] for p in s])) if s else None)
    L += ["", f"Strong-belief wrong answers (4/7 or more), n={len(strong)}: approved {100 * np.mean([p[1] for p in strong]):.0f}% "
          f"usually, {100 * np.mean([p[2] for p in strong]):.0f}% with the reference ({e[0]:+.0f} [{e[1]:+.0f}, {e[2]:+.0f}])."]
    (HERE / "out" / "reference_test.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def analyze_four():
    """Same BFF items under four prompts: usual, commit first, + reference, commit first + reference."""
    jobs, _, rows = load()
    def verdicts(fname, prefix):
        g = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / fname))}
        return {k: parse_verdict(v["text"]) for k, v in g.items() if k.startswith(prefix)}
    cf, rf, both = verdicts("gen_solvefirst.jsonl", "solvefirst|"), verdicts("gen_bffref.jsonl", "bffref|"), verdicts("gen_bffrefcf.jsonl", "bffrefcf|")
    P = []  # (qid, usual, cf, ref, both, ok, judge, bin)
    for (judge, iid), r in rows.items():
        k = f"{judge}|{iid}"
        v = (r.get("spoken"), cf.get("solvefirst|" + k), rf.get("bffref|" + k), both.get("bffrefcf|" + k))
        if any(x is None for x in v):
            continue
        P.append((jobs[(judge, iid)]["qid"], *[int(x) for x in v], int(r["target_ok"]), judge, binof(r["belief"])))
    names = ["usual judge prompt", "commit first", "+ expert reference", "commit first + reference"]
    L = ["# Four prompts on the same BFF items (three Qwens, thinking off)\n",
         f"{len(P)} items judged under all four prompts. 95% intervals resample questions.\n",
         "## Wrong answers approved\n", "| prompt | " + " | ".join(BINS) + " | strong belief (4/7+) |", "|---|---|---|---|---|---|"]
    for i, nm in enumerate(names, start=1):
        cells = []
        for b in BINS:
            v = [p[i] for p in P if p[5] == 0 and p[7] == b]
            cells.append(f"{100 * np.mean(v):.0f}% (n={len(v)})" if v else "–")
        st = [p[i] for p in P if p[5] == 0 and p[7] in ("4-6", "7/7")]
        L.append(f"| {nm} | " + " | ".join(cells) + f" | {100 * np.mean(st):.0f}% (n={len(st)}) |")
    L += ["", "## Right answers approved\n", "| prompt | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
    for i, nm in enumerate(names, start=1):
        cells = []
        for b in BINS:
            v = [p[i] for p in P if p[5] == 1 and p[7] == b]
            cells.append(f"{100 * np.mean(v):.0f}%" if v else "–")
        L.append(f"| {nm} | " + " | ".join(cells) + " |")
    def ba(s, i):
        pos = [p[i] for p in s if p[5] == 1]; neg = [1 - p[i] for p in s if p[5] == 0]
        return None if not pos or not neg else 100 * (np.mean(pos) + np.mean(neg)) / 2
    L += ["", "## Balanced accuracy (change vs usual, 95% interval)\n", "| prompt | all three | 4B | 9B | 35B |", "|---|---|---|---|---|"]
    for i, nm in enumerate(names, start=1):
        cells = []
        for j in [None] + QWENS:
            sub = [p for p in P if j is None or p[6] == j]
            if i == 1:
                cells.append(f"{ba(sub, 1):.1f}%")
            else:
                d = boot(sub, lambda s, i=i: (ba(s, i) - ba(s, 1)) if ba(s, i) is not None and ba(s, 1) is not None else None)
                cells.append(f"{ba(sub, i):.1f}% ({d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}])")
        L.append(f"| {nm} | " + " | ".join(cells) + " |")
    d = boot(P, lambda s: (ba(s, 4) - ba(s, 3)) if ba(s, 4) is not None and ba(s, 3) is not None else None)
    L += ["", f"Commit first + reference vs reference alone: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}] balanced accuracy."]
    (HERE / "out" / "reference_four.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def analyze_kimi():
    """Usual vs expert reference vs Kimi-K3.1-Pro reference, same BFF items; split by whether Kimi was right."""
    jobs, _, rows = load()
    def verdicts(fname, prefix):
        g = {r["cache_key"]: r for r in map(json.loads, open(HERE / "out" / fname))}
        return {k: parse_verdict(v["text"]) for k, v in g.items() if k.startswith(prefix)}
    rf, kf = verdicts("gen_bffref.jsonl", "bffref|"), verdicts("gen_bffkimi.jsonl", "bffkimi|")
    kok = {}
    for x in map(json.loads, open(HERE.parent / "beyond_capability" / "out" / "bff_grades_glm.jsonl")):
        m, uid, turn, si = x["cache_key"].split("|")
        if m == "kimi-k3.1-pro" and si == "0":
            kok[f"{uid}|{turn}"] = int(x["verdict"])
    P = []  # (qid, usual, expert, kimi, ok, judge, bin, kimi_right)
    for (judge, iid), r in rows.items():
        k = f"{judge}|{iid}"; j = jobs[(judge, iid)]
        v = (r.get("spoken"), rf.get("bffref|" + k), kf.get("bffkimi|" + k))
        if any(x is None for x in v):
            continue
        kq = f"{j['uid']}|{j['qid'].rsplit('-t', 1)[1]}"
        P.append((j["qid"], *[int(x) for x in v], int(r["target_ok"]), judge, binof(r["belief"]), kok.get(kq)))
    names = ["usual judge prompt", "+ expert reference", "+ Kimi-K3.1-Pro reference"]
    def ba(s, i):
        pos = [p[i] for p in s if p[4] == 1]; neg = [1 - p[i] for p in s if p[4] == 0]
        return None if not pos or not neg else 100 * (np.mean(pos) + np.mean(neg)) / 2
    def table(S, title):
        L = [f"## {title} ({len(S)} judgments)\n", "Wrong answers approved:\n",
             "| prompt | " + " | ".join(BINS) + " | strong belief (4/7+) | right answers approved | balanced accuracy (vs usual) |",
             "|---|---|---|---|---|---|---|---|"]
        for i, nm in enumerate(names, start=1):
            cells = []
            for b in BINS:
                v = [p[i] for p in S if p[4] == 0 and p[6] == b]
                cells.append(f"{100 * np.mean(v):.0f}% (n={len(v)})" if v else "–")
            st = [p[i] for p in S if p[4] == 0 and p[6] in ("4-6", "7/7")]
            rt = [p[i] for p in S if p[4] == 1]
            if i == 1:
                bc = f"{ba(S, 1):.1f}%"
            else:
                d = boot(S, lambda s, i=i: (ba(s, i) - ba(s, 1)) if ba(s, i) is not None and ba(s, 1) is not None else None)
                bc = f"{ba(S, i):.1f}% ({d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}])"
            L.append(f"| {nm} | " + " | ".join(cells) + f" | {100 * np.mean(st):.0f}% (n={len(st)}) | {100 * np.mean(rt):.0f}% | {bc} |")
        return L + [""]
    L = ["# Strong-model reference on BFF (three Qwens, thinking off)\n",
         "Kimi-K3.1-Pro's own answer (one sample, no expert involved) replaces the expert reference. 95% intervals resample questions.\n"]
    L += table(P, "All items")
    L += table([p for p in P if p[7] == 1], "Kimi's reference right")
    L += table([p for p in P if p[7] == 0], "Kimi's reference wrong")
    d = boot(P, lambda s: (ba(s, 3) - ba(s, 2)) if ba(s, 3) is not None and ba(s, 2) is not None else None)
    L += [f"Kimi reference vs expert reference: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}] balanced accuracy.",
          f"Kimi right on {sum(p[7] == 1 for p in P)} of {len(P)} judgments ({100 * np.mean([p[7] == 1 for p in P]):.0f}%)."]
    (HERE / "out" / "reference_kimi.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    prep() if "--prep" in sys.argv else prep_both() if "--prep-both" in sys.argv else prep_kimi() if "--prep-kimi" in sys.argv else analyze_kimi() if "--kimi" in sys.argv else analyze_four() if "--four" in sys.argv else analyze()
