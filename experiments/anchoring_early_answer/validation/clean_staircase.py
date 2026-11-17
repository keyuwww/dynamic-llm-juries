"""Does the belief staircase survive label cleaning? (Nov 16)
Labels: GLM-5.3 audit of every wrong-labelled BFF / JudgeBench answer in the Qwen belief rows (all belief levels,
out/ask_glm5.3_labelaudit.jsonl), plus Claude's reading of the 7/7 ones (validation/label_audit_7of7_results.jsonl).
RB2 Math rows already use the value-match cleaning (belief_rows_clean.json). Writes validation/clean_staircase.md.
"""
import json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parents[1]
V = HERE / "validation"
rows = json.load(open(HERE / "out" / "belief_rows_clean.json"))
glm = {}
for l in open(HERE / "out" / "ask_glm5.3_labelaudit.jsonl"):
    r = json.loads(l)
    m = re.findall(r"AUDIT:\s*(LABEL_OK|LABEL_WRONG|CONTESTED)", r["text"])
    glm[r["cache_key"].split("|", 2)[2]] = m[-1] if m else None
cl = {json.loads(l)["item"]: json.loads(l)["verdict"] for l in open(V / "label_audit_7of7_results.jsonl")}
def claude(item):
    for k, v in cl.items():
        if item.endswith(k) or k in item:
            return v
BINS = ["0/7", "1-3", "4-6", "7/7"]
def binof(r):
    k = round(float(r["belief"]) * 7)
    return "0/7" if k == 0 else "1-3" if k <= 3 else "4-6" if k <= 6 else "7/7"
W = [dict(r, b=binof(r), acc=int(r["spoken"])) for r in rows if int(r["target_ok"]) == 0 and r["spoken"] not in (None, "None")]
rng = np.random.default_rng(0)
def stair(S):
    return [np.mean([r["acc"] for r in S if r["b"] == b]) if any(r["b"] == b for r in S) else np.nan for b in BINS]
def boot_gap(S, n=2000):
    q = sorted({r["item"].rsplit("-", 0)[0] for r in S})
    by = {}
    for r in S:
        by.setdefault(r["item"], []).append(r)
    items = list(by)
    gaps = []
    for _ in range(n):
        smp = [r for i in rng.choice(len(items), len(items)) for r in by[items[i]]]
        s = stair(smp)
        gaps.append(s[3] - s[0])
    return np.nanpercentile(gaps, [2.5, 97.5])
def keep_all(r): return True
def no_glm_wrong(r): return r["bench"] == "rb2math" or glm.get(r["item"]) != "LABEL_WRONG"
def glm_ok(r): return r["bench"] == "rb2math" or glm.get(r["item"]) == "LABEL_OK"
def strict(r):  # GLM says OK at every level, and Claude also says OK where it read the item (7/7)
    if r["bench"] == "rb2math":
        return True
    c = claude(r["item"]) if r["b"] == "7/7" else None
    return glm.get(r["item"]) == "LABEL_OK" and c in (None, "LABEL_OK")
L = ["# Belief staircase after label cleaning (three Qwens, thinking off)\n",
     "Wrong answers approved, by how often the judge reaches that answer itself (0/7 .. 7/7). Gap = 7/7 minus 0/7, "
     "95% interval resampling answers. RB2 Math rows keep the earlier value-match cleaning in every version.\n",
     "| labels | " + " | ".join(BINS) + " | gap 7/7 − 0/7 |", "|---|---|---|---|---|---|"]
for name, f in [("as released", keep_all), ("drop GLM-5.3 'actually correct'", no_glm_wrong),
                ("only GLM-5.3 'clearly wrong'", glm_ok), ("GLM-5.3 and Claude both 'clearly wrong'", strict)]:
    S = [r for r in W if f(r)]
    s = stair(S); lo, hi = boot_gap(S)
    cells = [f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})" for v, b in zip(s, BINS)]
    L.append(f"| {name} | " + " | ".join(cells) + f" | {100 * (s[3] - s[0]):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}] |")
L += ["", "## By benchmark (only GLM-5.3 'clearly wrong')\n", "| bench | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
for bench in ["rb2math", "bff", "judgebench"]:
    S = [r for r in W if glm_ok(r) and r["bench"] == bench]
    L.append(f"| {bench} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})" for v, b in zip(stair(S), BINS)) + " |")
L += ["", "## By judge (only GLM-5.3 'clearly wrong')\n", "| judge | " + " | ".join(BINS) + " |", "|---|---|---|---|---|"]
for j in ["qwen3.5-4b", "qwen3.5-9b", "qwen3.6-35b-a3b"]:
    S = [r for r in W if glm_ok(r) and r["judge"] == j]
    L.append(f"| {j} | " + " | ".join(f"{100 * v:.0f}%" for v in stair(S)) + " |")
# audit verdict shares by belief bin (unique items)
L += ["", "## How many 'wrong' answers are actually wrong, by belief level (GLM-5.3, unique answers, BFF + JudgeBench)\n",
      "| belief | clearly wrong | actually correct | contested | approval if actually correct |", "|---|---|---|---|---|"]
for b in BINS:
    S = [r for r in W if r["b"] == b and r["bench"] != "rb2math"]
    its = {r["item"] for r in S}
    v = [glm.get(i) for i in its]
    ac = [r["acc"] for r in S if glm.get(r["item"]) == "LABEL_WRONG"]
    L.append(f"| {b} | {v.count('LABEL_OK')} | {v.count('LABEL_WRONG')} | {v.count('CONTESTED')} | "
             + (f"{100 * np.mean(ac):.0f}% (n={len(ac)})" if ac else "–") + " |")
# agreement with Claude on the 7/7 items
pairs = [(glm.get(next(i for i in glm if i.endswith(k) or k in i), None) if any(i.endswith(k) or k in i for i in glm) else None, v) for k, v in cl.items()]
pairs = [(g, c) for g, c in pairs if g]
agree = np.mean([g == c for g, c in pairs])
ok2 = np.mean([(g == "LABEL_OK") == (c == "LABEL_OK") for g, c in pairs])
L += ["", f"GLM-5.3 vs Claude on the {len(pairs)} answers believed 7/7: same three-way verdict {100 * agree:.0f}%, "
      f"same 'clearly wrong or not' call {100 * ok2:.0f}%."]
(V / "clean_staircase.md").write_text("\n".join(L) + "\n")
print("\n".join(L))


# ---- every judge family (Nov 16): Qwens, Nemotron-3-Super, DeepSeek-V4.1-Flash; C readout = spoken verdict
FAM = [("Qwen3.5-4B / 9B / Qwen3.6-35B (Alibaba)", "out"), ("Nemotron-3-Super-120B (NVIDIA)", "out_nemotron"),
       ("DeepSeek-V4.1-Flash (DeepSeek)", "out_deepseek"), ("Kimi-K2.6 (Moonshot)", "out_kimi")]
L2 = ["", "## Every judge family: as released vs only GLM-5.3 'clearly wrong'\n",
      "Answers not in the audit are kept as released. Gap = 7/7 minus 0/7 with a 95% interval resampling answers.\n",
      "| judge | labels | 0/7 | 1-3 | 4-6 | 7/7 | gap |", "|---|---|---|---|---|---|---|"]
for name, od in FAM:
    R = json.load(open(HERE / od / "belief_rows_clean.json"))
    WW = [dict(r, b=binof(r), acc=int(r["spoken"] if od == "out" else r["acc_C"]))
          for r in R if int(r["target_ok"]) == 0 and (r["spoken"] if od == "out" else r["acc_C"]) not in (None, "None")]
    for lab, f in [("as released", keep_all), ("clean", lambda r: r["bench"] == "rb2math" or glm.get(r["item"], "LABEL_OK") == "LABEL_OK")]:
        S = [r for r in WW if f(r)]
        s = stair(S); lo, hi = boot_gap(S)
        L2.append(f"| {name} | {lab} | " + " | ".join(f"{100 * v:.0f}% (n={sum(r['b'] == b for r in S)})" for v, b in zip(s, BINS))
                  + f" | {100 * (s[3] - s[0]):+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}] |")
with open(V / "clean_staircase.md", "a") as f:
    f.write("\n".join(L2) + "\n")
print("\n".join(L2))
