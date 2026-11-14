"""Anchoring analysis for an open judge outside Tinker (Llama-3.1-8B, OLMo-3 stages), and the cross-family test.

Inputs (<dst> = out_llama for Llama, out_open/<key> for OLMo):
  <dst>/solves.jsonl, judgments.jsonl                  open_ingest.py
  out/matches_glm5.3-flash_<key>.jsonl                 tinker_jobs.py --phase match --open <key>
  out/fill_glm5.3-flash_<key>.jsonl                    tinker_jobs.py --phase fill --open <key> (verdicts / BBEH
                                                       answers the judge did not write in the requested format)
  verdict margins at each checkpoint: <dst>/readouts.jsonl (probe_steer.py --phase readout: A, 25, 50, 75, E, C)
                                      or, for Llama, out_probe/llama3.1-8b/meta.jsonl (A only)
  out/rows.json                                        the Qwen rows (analyze.py)

acc_<ckpt> = accepts the target at that checkpoint (log-odds > 0); acc_S = the spoken verdict (exact parse, else GLM).

  python3 experiments/anchoring_early_answer/open_analysis.py --key olmo3-7b-instruct
"""
import argparse
import collections
import gzip
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze import MAIN, _cluster_boot, _fe_effect, letter, norm  # noqa: E402
from open_ingest import LLAMA, paths  # noqa: E402

CKS = ["A", "25", "50", "75", "E", "C"]


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def build_rows(KEY):
    _, O = paths(KEY)
    with gzip.open(HERE / "inputs" / "readout_jobs.jsonl.gz", "rt") as f:
        jobs = {j["item_id"]: j for j in map(json.loads, f) if j["judge"] == "qwen3.5-4b"}
    solves = {r["qid"]: r for r in load(O / "solves.jsonl")}
    judg = {r["item_id"]: r for r in load(O / "judgments.jsonl")}
    matches = {r["cache_key"]: r["verdict"] for r in load(HERE / "out" / f"matches_glm5.3-flash_{KEY}.jsonl")}
    fill = {r["cache_key"]: r["verdict"] for r in load(HERE / "out" / f"fill_glm5.3-flash_{KEY}.jsonl")}
    to_spoken = {"CORRECT": 1, "A": 1, "INCORRECT": 0, "B": 0}
    margin = collections.defaultdict(dict)
    if (O / "readouts.jsonl").exists():
        for r in load(O / "readouts.jsonl"):
            margin[r["item_id"]][r["ckpt"]] = r["margin"]
    else:
        for m in load(HERE / "out_probe" / KEY / "meta.jsonl"):
            margin[m["item_id"]]["A"] = m["margin"]
    pool = {}
    for line in open(HERE.parent / "tinker_pool" / "bbeh_results" / "answers.jsonl"):
        r = json.loads(line)
        pool[(r["model"], r["item"])] = norm(r["answer"])

    rows, n_fill_v = [], 0
    for iid, j in jobs.items():
        if iid not in judg or "A" not in margin.get(iid, {}):
            continue
        sp = judg[iid]["spoken"]
        if sp is None:  # no "VERDICT:" line: the verdict GLM read from the transcript (None if it found none)
            sp = to_spoken.get(fill.get(f"{KEY}|{iid}"))
            n_fill_v += sp is not None
        if j["bench"] == "bbeh":
            q, exam = iid.split("|")
            own = norm(solves[q]["answer"]) if q in solves else None
            cand = pool.get((exam, q))
            if cand is None:
                continue
            if own is not None:
                same = own == cand
            else:  # no "The answer is" line: GLM compared the judge's answer with the candidate
                v = fill.get(f"{KEY}|{iid}|0")
                if v not in ("SAME", "DIFFERENT"):
                    continue
                same = v == "SAME"
            group, sign, ok = ("match" if same else "differ"), 1, int(j["gold"])
        elif j["bench"] in ("rb2math", "bff"):
            v = matches.get(f"{KEY}|{iid}|0")
            if v not in ("SAME", "DIFFERENT"):
                continue
            group, sign, ok = ("match" if v == "SAME" else "differ"), 1, int(j["gold"])
        else:
            own_l = letter(solves.get(j["qid"], {}).get("answer"))
            vs = []
            for ci, cand in enumerate(j["candidates"]):
                cl = letter(cand)
                vs.append(("SAME" if own_l == cl else "DIFFERENT") if own_l and cl else matches.get(f"{KEY}|{iid}|{ci}"))
            if None in vs or "NONE" in vs or vs.count("SAME") == 2:
                continue
            tgt_a = vs[0] == "SAME" if vs.count("SAME") == 1 else j["gold"] == 0
            group = "match" if vs.count("SAME") == 1 else "differ"
            sign, ok = (1 if tgt_a else -1), int(j["gold"] == (1 if tgt_a else 0))
        r = dict(bench=j["bench"], judge=KEY, item=iid, group=group, target_ok=ok, spoken=sp, q=j.get("uid"))
        for ck in CKS:
            m = margin[iid].get(ck)
            r[f"acc_{ck}"] = None if m is None else int(sign * m > 0)
        r["acc_S"] = None if sp is None else (int(sp == 1) if sign == 1 else int(sp == 0))
        rows.append(r)
    return rows, solves, judg, n_fill_v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=LLAMA)
    a = ap.parse_args()
    KEY = a.key
    _, O = paths(KEY)
    rows, solves, judg, n_fill_v = build_rows(KEY)
    cks = [c for c in CKS if any(r[f"acc_{c}"] is not None for r in rows)] + ["S"]
    name = {"A": "A (before writing)", "E": "E (end of thinking)", "C": "C (readout at verdict)", "S": "spoken verdict"}
    qwen_rows = json.load(open(HERE / "out" / "rows.json"))

    fin = sum(s["clean"] for s in solves.values())
    L = [f"# {KEY} — anchoring and the cross-family test\n",
         f"Own answers: {len(solves)} questions, {fin} finished within 64K tokens. Judgments: {len(judg)}; spoken "
         f"verdict in the requested format: {sum(v['spoken'] is not None for v in judg.values())}, + {n_fill_v} read "
         f"by GLM. Analysed rows: {len(rows)}. Checkpoints: {', '.join(cks)}.\n",
         "## 0. Does it tell right from wrong? Accept rate (right / wrong candidate)\n",
         "| Benchmark | " + " | ".join(name.get(c, c + "%") for c in cks) + " |", "|---|" + "---|" * len(cks)]
    for b in ("rb2math", "judgebench", "bff", "bbeh"):
        cells = []
        for c in cks:
            R = [r for r in rows if r["bench"] == b and r[f"acc_{c}"] is not None]
            ok_ = [r[f"acc_{c}"] for r in R if r["target_ok"] == 1]
            bad = [r[f"acc_{c}"] for r in R if r["target_ok"] == 0]
            cells.append(f"{np.mean(ok_):.2f} / {np.mean(bad):.2f}" if ok_ and bad else "–")
        L.append(f"| {b} | " + " | ".join(cells) + " |")

    L += ["\n## 1. Wrong candidates: accept rate by checkpoint, own answer matches vs differs\n",
          "| Benchmark | Group | n | " + " | ".join(cks) + " |", "|---|---|---|" + "---|" * len(cks)]
    for b in ("rb2math", "judgebench", "bff", "bbeh"):
        for g in ("match", "differ"):
            R = [r for r in rows if r["bench"] == b and r["group"] == g and r["target_ok"] == 0 and r["acc_S"] is not None]
            if R:
                L.append(f"| {b} | {g} | {len(R)} | " + " | ".join(
                    f"{np.mean([r[f'acc_{c}'] for r in R if r[f'acc_{c}'] is not None]):.2f}"
                    if any(r[f"acc_{c}"] is not None for r in R) else "–" for c in cks) + " |")

    W = [r for r in rows if r["target_ok"] == 0 and r["acc_S"] is not None]

    def gap(ck):
        def f(R):
            R = [r for r in R if r[f"acc_{ck}"] is not None]
            return (np.mean([r[f"acc_{ck}"] for r in R if r["group"] == "match"])
                    - np.mean([r[f"acc_{ck}"] for r in R if r["group"] == "differ"]))
        return f

    def rescue(R):
        return (np.mean([1 - r["acc_S"] for r in R if r["group"] == "differ" and r["acc_A"] == 1])
                - np.mean([1 - r["acc_S"] for r in R if r["group"] == "match" and r["acc_A"] == 1]))
    gcks = [c for c in ("A", "E", "S") if c in cks]
    L += ["\nGap = accept rate when the wrong answer matches the judge's own minus when it differs; rescue gap = how "
          "much more often reasoning overturns an accept-at-A when the judge's answer differs. 95% intervals, questions "
          "resampled.\n",
          "| Benchmark | " + " | ".join(f"Gap at {name[c]}" for c in gcks) + " | Rescue gap |",
          "|---|" + "---|" * (len(gcks) + 1)]
    for b in ("main", "rb2math", "judgebench", "bff", "bbeh"):
        R = [r for r in W if r["bench"] in MAIN] if b == "main" else [r for r in W if r["bench"] == b]
        cells = [_cluster_boot(R, f, 2000) for f in [gap(c) for c in gcks] + [rescue]]
        L.append(f"| {b} | " + " | ".join(f"{e:+.2f} [{lo:+.2f}, {hi:+.2f}]" for e, lo, hi in cells) + " |")

    # cross-family: Qwen belief count for each wrong single-answer candidate
    qbel = collections.defaultdict(int)
    for r in qwen_rows:
        if r["bench"] != "judgebench" and r["target_ok"] == 0 and r["group"] == "match":
            qbel[(r["bench"], r["item"])] += 1
    L += ["\n## 2. Cross-family: does it accept the wrong answers the Qwens believe?\n",
          "Wrong single-answer candidates. 'Qwens who gave it' = how many of the 3 Qwens produced that same wrong "
          "answer when solving. Split by whether this judge's own answer matches.\n",
          "| Own answer | Qwens who gave it | n | accepts at A | spoken |", "|---|---|---|---|---|"]
    for g in ("differ", "match"):
        for k in (0, 1, 2, 3):
            R = [r for r in W if r["bench"] != "judgebench" and r["group"] == g and qbel[(r["bench"], r["item"])] == k]
            if len(R) >= 5:
                L.append(f"| {g}s | {k} | {len(R)} | {np.mean([r['acc_A'] for r in R]):.2f} | "
                         f"{np.mean([r['acc_S'] for r in R]):.2f} |")
    D = [dict(r, k=qbel[(r["bench"], r["item"])]) for r in W if r["bench"] != "judgebench" and r["group"] == "differ"]

    def contrast(ck):
        return lambda R: (np.mean([r[f"acc_{ck}"] for r in R if r["k"] >= 2])
                          - np.mean([r[f"acc_{ck}"] for r in R if r["k"] == 0]))
    L.append("\nWhen its own answer differs: accept rate for wrong answers 2–3 Qwens gave minus wrong answers no Qwen "
             "gave (95% interval, questions resampled):\n")
    for ck in ("A", "S"):
        e, lo, hi = _cluster_boot(D, contrast(ck), 2000)
        L.append(f"- {name[ck]}: {e:+.2f} [{lo:+.2f}, {hi:+.2f}]")

    # same-candidate control: 3 Qwens + this judge (caveat in REPORT: mixes own belief with family)
    allr = ([dict(r, acc_C=r.get("acc_C")) for r in qwen_rows if r["bench"] != "judgebench"]
            + [dict(r, acc_C=r["acc_S"]) for r in rows if r["bench"] != "judgebench"])
    WW = [r for r in allr if r["target_ok"] == 0 and r.get("acc_A") is not None and r.get("acc_C") is not None]
    L += ["\n## 3. Same wrong candidate, 3 Qwens + this judge (judge + candidate fixed effects)\n",
          "| | effect of 'matches my own answer' |", "|---|---|"]
    for ck in ("A", "C"):
        e, lo, hi = _cluster_boot(WW, lambda X, ck=ck: _fe_effect(X, ck), 500)
        L.append(f"| {ck} | {e:+.3f} [{lo:+.3f}, {hi:+.3f}] |")
    text = "\n".join(L) + "\n"
    (O / "results.md").write_text(text)
    # acc_C in rows.json = the spoken verdict, as probes.py / steer_analysis.py expect
    json.dump([dict(r, acc_Cr=r["acc_C"], acc_C=r["acc_S"]) for r in rows], open(O / "rows.json", "w"))
    print(text)


if __name__ == "__main__":
    main()
