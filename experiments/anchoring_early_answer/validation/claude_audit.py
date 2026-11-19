"""Compare the Claude Opus 5.5 label audit (third auditor) with GLM-5.3 and Kimi-K3.1-Pro (Nov 18).
Inputs: OUTDIR/map.json and OUTDIR/results/NNN.json from build_claude_audit.py + the auditing agents.
Writes validation/claude_audit_results.jsonl (one row per answer) and validation/claude_audit.md.
The 60-answer sample was drawn stratified on GLM's verdict (25 clearly wrong, 25 actually correct, 10 contested), so
raw agreement on it over-weights GLM's minority calls; we report it per stratum and re-weighted to GLM's full mix.
usage: python claude_audit.py OUTDIR
"""
import json, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1])
M = json.load(open(OUT / "map.json"))
rows = []
for m in M:
    f = OUT / "results" / f"{m['i']:03d}.json"
    r = json.load(open(f)) if f.exists() else {}
    rows.append({**m, "claude": r.get("verdict"), "claude_answer": r.get("correct_answer"), "claude_reason": r.get("reason")})
with open(HERE / "claude_audit_results.jsonl", "w") as fh:
    for r in rows:
        fh.write(json.dumps(r) + "\n")

ok = lambda v: v == "LABEL_OK"
def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n; pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")

L = ["# Third label auditor: Claude Opus 5.5\n",
     f"Answers audited: {len(rows)}; missing Claude verdicts: {sum(r['claude'] is None for r in rows)}\n"]
S = [r for r in rows if r["in_sample"] and r["claude"]]
L.append(f"## Blind 60-answer sample (stratified on GLM's verdict), n = {len(S)}\n")
L.append("| GLM verdict | n | Claude: clearly wrong | actually correct | contested |\n|---|---|---|---|---|")
for g in ["LABEL_OK", "LABEL_WRONG", "CONTESTED"]:
    c = Counter(r["claude"] for r in S if r["glm"] == g)
    L.append(f"| {g} | {sum(c.values())} | {c['LABEL_OK']} | {c['LABEL_WRONG']} | {c['CONTESTED']} |")
for name in ["glm", "kimi"]:
    P = [r for r in S if r[name]]
    a, b = [ok(r["claude"]) for r in P], [ok(r[name]) for r in P]
    L.append(f"\nClaude vs {name} (clearly-wrong-or-not), sample: {sum(x == y for x, y in zip(a, b))}/{len(P)} agree, kappa {kappa(a, b):.2f}")
# re-weight sample agreement with GLM to GLM's full-population mix (978 OK / 62 WRONG / 48 CONTESTED of 1,088 with a verdict)
W = {"LABEL_OK": 978, "LABEL_WRONG": 62, "CONTESTED": 48}
acc = {g: sum(ok(r["claude"]) == ok(g) for r in S if r["glm"] == g) / max(1, sum(r["glm"] == g for r in S)) for g in W}
L.append(f"Agreement with GLM re-weighted to GLM's full mix: {sum(W[g] * acc[g] for g in W) / sum(W.values()):.1%} "
         f"(per stratum: " + ", ".join(f"{g} {acc[g]:.0%}" for g in W) + ")")
# all three on the sample
three = [r for r in S if r["glm"] and r["kimi"]]
L.append(f"All three auditors make the same clearly-wrong-or-not call on {sum(ok(r['glm']) == ok(r['kimi']) == ok(r['claude']) for r in three)}/{len(three)} sample answers")
D = [r for r in rows if r["disagree"] and r["claude"]]
side = Counter("GLM" if ok(r["claude"]) == ok(r["glm"]) else "Kimi" for r in D)
L.append(f"\n## GLM/Kimi disagreements, n = {len(D)}\nClaude sides with GLM on {side['GLM']}, with Kimi on {side['Kimi']}.")
L.append("Claude's verdicts there: " + ", ".join(f"{k} {v}" for k, v in Counter(r['claude'] for r in D).items()))
c = Counter((r["glm"], r["kimi"], r["claude"]) for r in D)
L.append("\n| GLM | Kimi | Claude | n |\n|---|---|---|---|")
L += [f"| {a} | {b} | {d} | {n} |" for (a, b, d), n in sorted(c.items(), key=lambda x: -x[1])]
L.append("\n## By benchmark (sample)\n")
for bench in ["bff", "judgebench", "rb2"]:
    P = [r for r in S if bench in r["cache_key"]]
    if P:
        L.append(f"- {bench}: Claude agrees with GLM on {sum(ok(r['claude']) == ok(r['glm']) for r in P)}/{len(P)}, with Kimi on {sum(ok(r['claude']) == ok(r['kimi']) for r in P if r['kimi'])}/{sum(bool(r['kimi']) for r in P)}")
open(HERE / "claude_audit.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
