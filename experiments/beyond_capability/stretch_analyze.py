"""Stretching results on a moderate benchmark (MMLU-Redux, MATH): for each judge, solved vs unsolved questions,
every edit: within-question AUROC (ranking right above wrong), balanced accuracy, accept rates; and the change from
stretching x11 along the judge direction vs no edit and vs a random direction, with question-resampled 95% intervals.

Inputs: out_<bench>/<model>/steer_<tag>_h{1,2}.jsonl and direction_choice_<tag>.json (copied from the cluster),
solve labels: Qwen-9B from Tinker (out/esolves_<stem>_qwen3.5-9b.jsonl, majority of 3), Llama-8B from the cluster
(out_<bench>/esolves_<stem>_llama3.1-8b.jsonl).

  python3 experiments/beyond_capability/stretch_analyze.py --bench mmlu --stem mmlu_full
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bc_load import OUT, boot_ci, jl, metrics, within_auc  # noqa: E402


def letter(text):
    m = re.findall(r"answer is:?\s*\**\s*\(?([A-J])\)?\b", text or "", re.I)
    return m[-1].upper() if m else None


def solve_labels(stem, model, bench_dir):
    qs = {q["id"]: q for q in jl(HERE / "inputs" / f"{stem}.jsonl")}
    grades = {r["cache_key"]: r["verdict"] for r in jl(OUT / f"egrades_{stem}.jsonl")}
    is_mc = stem.startswith("mmlu")

    def ok(fstem, qid, i, text):
        if is_mc:
            return int(letter(text) == qs[qid]["gold"])
        v = grades.get(f"{fstem}|{qid}|{i}")
        return None if v is None else int(v)
    out = {}
    if model.startswith("qwen"):
        f = f"esolves_{stem}_{model}"
        for r in jl(OUT / f"{f}.jsonl"):
            v = [ok(f, r["qid"], i, s["text"]) for i, s in enumerate(r["samples"])]
            if None not in v:
                out[r["qid"]] = int(sum(v) * 2 > len(v))
    else:
        f = f"esolves_{stem}_{model}"
        for r in jl(bench_dir / f"{f}.jsonl"):
            v = 0 if r.get("capped") else ok(f, r["qid"], 0, r["text"])  # hit the length cap = looped = wrong
            if v is not None:
                out[r["qid"]] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="mmlu")
    ap.add_argument("--stem", default="mmlu_full")
    a = ap.parse_args()
    bdir = HERE / f"out_{a.bench}"
    L = [f"# Stretching the judge direction — {a.bench}\n",
         "Thinking off; the verdict is read at \"VERDICT:\" right after the edit. Directions are question-centred and "
         "learned on the other half of the questions. Cells: within-question AUROC / balanced accuracy "
         "(accept rate of right / of wrong answers).\n"]
    for model in ("qwen3.5-9b", "llama3.1-8b"):
        d = bdir / model
        rows = [json.loads(l) for p in sorted(d.glob(f"steer_{a.bench}_h*.jsonl")) for l in open(p)]
        if not rows:
            continue
        ch = json.load(open(d / f"direction_choice_{a.bench}.json"))
        sol = solve_labels(a.stem, model, bdir)
        groups = [(None, "all questions")] + ([(1, "solved"), (0, "not solved")] if sol else [])
        sel = lambda r, sv: sv is None or sol.get(r["qid"]) == sv  # noqa: E731
        L.append(f"\n## {model} (layer {ch['layer']}; held-out within-question AUROC of the direction "
                 f"{ch['scores'][str(ch['layer'])] if str(ch['layer']) in ch['scores'] else ch['scores'][ch['layer']]:.2f}; "
                 + (f"solves {np.mean(list(sol.values())):.0%} of questions)\n" if sol else "solve labels not available yet)\n"))
        L.append("| Direction | Edit | " + " | ".join(n for _, n in groups) + " |")
        L.append("|---|---|" + "---|" * len(groups))
        for dn in ("Jc", "Rc"):
            X = [r for r in rows if r["dir"].startswith(dn + "_")]
            keys = sorted(X[0]["margins"], key=lambda k: (k.split(":")[0] != "add", float(k.split(":")[1])))
            for k in keys:
                cells = []
                for sv, _ in groups:
                    S = [r for r in X if sel(r, sv)]
                    R = [dict(qid=r["qid"], gold=r["gold"], v=int(r["margins"][k] > 0)) for r in S]
                    m = metrics(R)
                    au = within_auc([r["gold"] for r in S], [r["margins"][k] for r in S], [r["qid"] for r in S])[0]
                    cells.append(f"{au:.2f} / {m['bal']:.2f} ({m['tpr']:.2f} / {m['fpr']:.2f}) n={m['n']}" if m["n"] else "–")
                L.append(f"| {'judge' if dn == 'Jc' else 'random'} | {k.replace(':', ' ')} | " + " | ".join(cells) + " |")
        L.append("\nStretch x11 (amplify 10) minus no edit, judge direction [95% CI]:\n")
        L.append("| Questions | Δ within-question AUROC | Δ balanced accuracy | same for the random direction (Δ bal.) |")
        L.append("|---|---|---|---|")
        for sv, nm in groups:
            out = []
            for dn in ("Jc", "Rc"):
                S = [r for r in rows if r["dir"].startswith(dn + "_") and sel(r, sv)]

                def dbal(rr):
                    mk = lambda k: [dict(qid=r["qid"], gold=r["gold"], v=int(r["margins"][k] > 0)) for r in rr]  # noqa: E731
                    return metrics(mk("amplify:10.0"))["bal"] - metrics(mk("add:0.0"))["bal"]

                def dauc(rr):
                    y = [r["gold"] for r in rr]
                    g = [r["qid"] for r in rr]
                    return (within_auc(y, [r["margins"]["amplify:10.0"] for r in rr], g)[0]
                            - within_auc(y, [r["margins"]["add:0.0"] for r in rr], g)[0])
                b = boot_ci(S, dbal, n=500)
                if dn == "Jc":
                    u = boot_ci(S, dauc, n=500)
                    out += [f"{100 * dauc(S):+.0f} [{100 * u[0]:+.0f}, {100 * u[1]:+.0f}]", f"{100 * dbal(S):+.0f} [{100 * b[0]:+.0f}, {100 * b[1]:+.0f}]"]
                else:
                    out.append(f"{100 * dbal(S):+.0f} [{100 * b[0]:+.0f}, {100 * b[1]:+.0f}]")
            L.append(f"| {nm} | " + " | ".join(out) + " |")
    (bdir / f"stretch_tables_{a.bench}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
