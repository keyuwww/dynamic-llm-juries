"""Score the stretch with alternative directions (make_alt_dirs.py) against MMLU's own direction, one judge.
Gain = ranking (within-question AUROC) after stretching minus unedited, x100, 95% CI by resampling questions
(2000 draws, seed 0). Groups: all answers, questions the judge solves / doesn't solve, and same-model pairs.

  python score_alt_dirs.py out_mmlu/llama3.1-8b out/esolves_mmlu_full_llama3.1-8b.jsonl math
    -> <mmlu dir>/alt_dirs_outcome.md
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prereg_score_gnr import gain_ci, letter, table  # noqa: E402

STR = {"amplify:1.0": 2, "amplify:3.0": 4, "amplify:10.0": 11}


def main():
    md, sfile, stag = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    rng = np.random.default_rng(0)
    gold = {json.loads(l)["id"]: json.loads(l)["gold"] for l in open("inputs/mmlu_full.jsonl")}
    sol = {}
    for l in open(sfile):
        r = json.loads(l)
        capped = r.get("capped", str(r.get("clean", True)) in ("False", "false", "0"))
        sol[r["qid"]] = 0 if capped else int(letter(r["text"]) == gold[r["qid"]])
    rows = [json.loads(l) for h in ("h1", "h2") for f in (f"steer_mmlu_{h}.jsonl", f"steer_mmlualt_T_{h}.jsonl")
            for l in open(md / f)]
    for r in rows:
        r["src"] = r["aid"].split("|")[1]
    dirs = {"Jc": "MMLU's own (original)", "Bm": f"borrowed from {stag}", "Sm": "same-model pairs only", "Rc": "random"}
    groups = {"all": lambda r: True, "solved": lambda r: sol.get(r["qid"]) == 1,
              "not solved": lambda r: sol.get(r["qid"]) == 0}
    nsol = sum(sol.values())
    L = [f"# {md.name}: stretching MMLU with a borrowed and a same-model direction\n",
         f"Judge solves {nsol} of {len(sol)} questions ({nsol / len(sol):.0%}). Gain = ranking change x100 [95% CI].\n"]
    for same in (False, True):
        L += [f"\n## {'Same-model pairs only' if same else 'All pairs'}\n",
              "| Direction | Group | Unedited | ×2 | ×4 | ×11 |", "|---|---|---|---|---|---|"]
        for dk, dn in dirs.items():
            for gk, gf in groups.items():
                R = [r for r in rows if r["dir"].startswith(dk) and gf(r)]
                if not R:
                    continue
                qs, A = table(R, ["add:0.0"] + list(STR), same_src=same)
                if len(qs) < 30:
                    continue
                base = A["add:0.0"].sum(0)
                cells = []
                for k in STR:
                    g, lo, hi = gain_ci(A["add:0.0"], A[k], rng)
                    cells.append(f"{g:+.1f} [{lo:+.1f}, {hi:+.1f}]")
                L.append(f"| {dn} | {gk} ({len(qs)} q) | {base[0] / base[1]:.3f} | " + " | ".join(cells) + " |")
    (md / "alt_dirs_outcome.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
