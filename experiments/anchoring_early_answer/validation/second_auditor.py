"""Second, independent label auditor (Nov 18): Kimi-K3.1-Pro (high reasoning; Moonshot, not one of the judges) re-audited
the same 460 wrong-labelled BFF / JudgeBench answers as GLM-5.3, with the same prompts (inputs/ask_labelaudit.jsonl.gz).
Agreement with GLM, and the staircase of every judge family under each auditor's labels and under both.

  python3 experiments/anchoring_early_answer/validation/second_auditor.py -> validation/second_auditor.md
"""
import collections
import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
V = HERE / "validation"
sys_path = str(V)
import sys  # noqa: E402
sys.path.insert(0, sys_path)
from think_staircase import binof, boot, stair  # noqa: E402

FAM = [("3 Qwens", "out"), ("Nemotron-3-Super", "out_nemotron"), ("DeepSeek-V4.1-Flash", "out_deepseek"),
       ("Kimi-K2.6", "out_kimi"), ("Nemotron-3-Nano", "out_nano")]
LAB = ["LABEL_OK", "LABEL_WRONG", "CONTESTED"]


def audit(name):
    g = {}
    for line in open(HERE / "out" / name):
        r = json.loads(line)
        m = re.findall(r"AUDIT:\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", r["text"])
        g[r["cache_key"].split("|", 2)[2]] = m[-1] if m else None
    return g


def main():
    glm = {**audit("ask_glm5.3_labelaudit.jsonl"), **audit("ask_glm5.3_labelauditrb2.jsonl")}
    kimi = {**audit("ask_kimi3.1pro_labelaudit.jsonl"), **audit("ask_kimi3.1pro_labelauditrb2.jsonl")}
    both = [i for i in glm if i in kimi and glm[i] and kimi[i]]
    L = ["# Second label auditor: Kimi-K3.1-Pro vs GLM-5.3\n",
         f"{len(both)} answers with a verdict from both (of {len(glm)}). Rows GLM-5.3, columns Kimi-K3.1-Pro.\n",
         "| GLM \\ Kimi | " + " | ".join(LAB) + " |", "|---|---|---|---|"]
    for a in LAB:
        L.append(f"| {a} | " + " | ".join(str(sum(glm[i] == a and kimi[i] == b for i in both)) for b in LAB) + " |")
    agree = np.mean([glm[i] == kimi[i] for i in both])
    ok2 = np.mean([(glm[i] == "LABEL_OK") == (kimi[i] == "LABEL_OK") for i in both])
    po = ok2
    pg = np.mean([glm[i] == "LABEL_OK" for i in both])
    pk = np.mean([kimi[i] == "LABEL_OK" for i in both])
    pe = pg * pk + (1 - pg) * (1 - pk)
    kappa = (po - pe) / (1 - pe)
    for bench in ("rb2math", "bff", "judgebench"):
        bb = [i for i in both if (i.startswith("rb2math") if bench == "rb2math" else (i.startswith("judgebench") if bench == "judgebench" else not (i.startswith("rb2math") or i.startswith("judgebench"))))]
        if bb:
            L.append(f"- {bench}: n={len(bb)}, same clearly-wrong-or-not call {100 * np.mean([(glm[i] == 'LABEL_OK') == (kimi[i] == 'LABEL_OK') for i in bb]):.0f}%")
    L += ["", f"Same three-way verdict: {100 * agree:.0f}%. Same 'clearly wrong or not' call: {100 * ok2:.0f}% "
              f"(Cohen's kappa {kappa:.2f}).", ""]
    # staircase per family under each label set
    L += ["## Staircase of wrong answers approved, by label set\n",
          "| judge | labels | 0/7 | 1-3 | 4-6 | 7/7 | gap |", "|---|---|---|---|---|---|---|"]
    sets = [("GLM-5.3 'clearly wrong'", lambda i: glm.get(i) == "LABEL_OK"),
            ("Kimi-K3.1-Pro 'clearly wrong'", lambda i: kimi.get(i) == "LABEL_OK"),
            ("both 'clearly wrong'", lambda i: glm.get(i) == "LABEL_OK" and kimi.get(i) == "LABEL_OK")]
    for name, od in FAM:
        R = json.load(open(HERE / od / "belief_rows_clean.json"))
        col = "spoken"  # the stated verdict for every family (as in paper_numbers.py)
        W = [dict(r, b=binof(r), on=int(r[col])) for r in R
             if int(r["target_ok"]) == 0 and r[col] not in (None, "None")]
        for lab, f in sets:
            S = [r for r in W if f(r["item"])]
            s = stair(S, "on")
            lo, hi = boot(S, "on")
            L.append(f"| {name} | {lab} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})"
                                                         for v, b in zip(s, ["0/7", "1-3", "4-6", "7/7"]))
                     + f" | {100 * (s[3] - s[0]):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}] |")
    (V / "second_auditor.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
