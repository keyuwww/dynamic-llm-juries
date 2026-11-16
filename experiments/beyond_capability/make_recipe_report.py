"""Fill the tables of report_2026-11-16-stretch-recipe.md from out_allpairs/allpairs.json (allpairs_analyze.py).
Placeholders TABLE_MAIN / TABLE_SM / DIAG / SENS in the template are replaced; the template text stays as written.

  python3 experiments/beyond_capability/make_recipe_report.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.load(open(HERE / "out_allpairs" / "allpairs.json"))
NAME = {"llama3.1-8b": "Llama-3.1-8B", "llama3.2-3b": "Llama-3.2-3B", "qwen3.5-9b": "Qwen3.5-9B",
        "qwen3.5-4b": "Qwen3.5-4B", "phi4-mini": "Phi-4-mini", "mistral-7b": "Mistral-7B", "granite3.3-8b": "Granite-3.3-8B"}
BN = {"mmlu": "MMLU", "math": "MATH", "bbeh": "BBEH"}


def f(x, ci=True):
    if not x:
        return "–"
    s = f"{x['g']:+.1f}"
    return f"**{s}** [{x['lo']:+.1f}, {x['hi']:+.1f}]" if ci and x["lo"] > 0 else (f"{s} [{x['lo']:+.1f}, {x['hi']:+.1f}]" if ci else s)


def main_table():
    L = ["| Bench | Judge | Gap | Layer | Accept −8 → +8 sd | Gain ×11, all | Solved | Not solved | Same-model, not solved |",
         "|---|---|---|---|---|---|---|---|---|"]
    nogap = []
    for b in ("mmlu", "math", "bbeh"):
        for j in NAME:
            o = R.get(f"{j}|{b}", {})
            if "gap" not in o:
                continue
            if "layer" not in o:
                nogap.append(f"{NAME[j]} on {BN[b]} ({o['gap']:+.1f})")
                continue
            nl = o.get("n_layers") or {"llama3.1-8b": 32, "llama3.2-3b": 28}.get(j, 32)
            star = "" if o["status"] == "responds" else "*"
            L.append(f"| {BN[b]} | {NAME[j]} | {o['gap']:+.1f} | {o['layer']}/{nl}{star} | {o['accept_m8']:.0f}% → {o['accept_p8']:.0f}% | "
                     f"{f(o.get('all | x11'))} | {f(o.get('solved | x11'))} | {f(o.get('not solved | x11'))} | "
                     f"{f(o.get('not solved | x11 | same-model'))} |")
    return "\n".join(L) + ("\n\n\\* No layer responds; stretched at the layer whose direction ranks best. "
                           "Not stretched (gap ≤ 5): " + "; ".join(nogap) + ".")


def sm_table():
    L = ["| Judge, benchmark (questions) | Questions | Ranking before | ×4 | ×11 | ×21 | Random ×11 |",
         "|---|---|---|---|---|---|---|"]
    rows = []
    for k, v in R.items():
        if not k.startswith("extra|"):
            continue
        _, pair, sub = k.split("|")
        j, b = pair.rsplit("_", 1)
        if j not in NAME:
            continue  # fresh judges have their own table (section 7)
        if sub != "judge itself can't solve" and f"extra|{pair}|judge itself can't solve" in R:
            continue  # show the judge's own unsolved set when we have it
        lab = "own unsolved" if (sub == "judge itself can't solve" or j == "llama3.1-8b") else (
            "all questions" if sub == "all questions" else "8B's unsolved")
        rows.append((b, j, f"| {NAME[j]}, {BN[b]} ({lab}) | {v['x11']['nq']} | {v['x11']['says']:.2f} | {f(v['x4'])} | "
                            f"{f(v['x11'])} | {f(v['x21'])} | {v['r']['g']:+.1f} |"))
    for k, v in R.items():
        if k.startswith("extra strict|") and "0 of 8" in k:
            rows.append(("math", "llama3.1-8b~", f"| Llama-3.1-8B, MATH (failed 9 of 9 own tries) | {v['x11']['nq']} | "
                                                  f"{v['x11']['says']:.2f} | {f(v['x4'])} | {f(v['x11'])} | {f(v['x21'])} | {v['r']['g']:+.1f} |"))
    rows.sort(key=lambda t: (t[0], t[1]))
    # pooled per benchmark: one entry per judge, its own-unsolved set where available (strict 9-try set excluded)
    import numpy as np
    pool = []
    for b in ("math", "bbeh", "mmlu"):
        cell = []
        for t in ("x4", "x11", "x21"):
            xs = []
            for j in NAME:
                v = R.get(f"extra|{j}_{b}|judge itself can't solve") or R.get(f"extra|{j}_{b}|Llama-3.1-8B can't solve")
                if v and v[t] and v[t]["hi"] > v[t]["lo"]:
                    xs.append(v[t])
            if not xs:
                cell.append("–")
                continue
            w = np.array([1 / ((x["hi"] - x["lo"]) / 3.92) ** 2 for x in xs])
            g = np.array([x["g"] for x in xs])
            m, se = (w * g).sum() / w.sum(), 1 / np.sqrt(w.sum())
            cell.append(f(dict(g=m, lo=m - 1.96 * se, hi=m + 1.96 * se)))
            k = len(xs)
        pool.append(f"| **Pooled, {BN[b]}** ({k} judges) | | | {cell[0]} | {cell[1]} | {cell[2]} | |")
    return "\n".join(L + [r[2] for r in rows] + pool)


def sens_table():
    L = ["| Judge, benchmark | Sensitivity | ×4 | ×11 | ×21 |", "|---|---|---|---|---|"]
    items = sorted(((v["sensitivity"], k, v) for k, v in R.items()
                    if "sensitivity" in v and v["sensitivity"] > 0 and k.split("|")[0] in NAME), reverse=True)
    for s_, k, v in items:
        j, b = k.split("|")
        g = lambda t: f(v.get(f"all | {t}"), ci=False)  # noqa: E731
        L.append(f"| {NAME[j]}, {BN[b]} | {s_:.2f} | {g('x4')} | {g('x11')} | {g('x21')} |")
    return "\n".join(L)


def fresh_table():
    FR = {"llama3.2-1b": "Llama-3.2-1B", "qwen2.5-7b": "Qwen2.5-7B"}
    L = ["| Bench | Judge | Gap | Layer: score rule (accept rule) | Sensitivity | Gain ×11, all | Not solved | "
         "Same-model, own unsolved: ×4 / ×11 | Random |", "|---|---|---|---|---|---|---|---|---|"]
    for b in ("mmlu", "math", "bbeh"):
        for j, nm in FR.items():
            o = R.get(f"{j}|{b}", {})
            if "gap" not in o:
                L.append(f"| {BN[b]} | {nm} | pending | | | | | | |")
                continue
            if "layer" not in o:
                L.append(f"| {BN[b]} | {nm} | {o['gap']:+.1f} | gap ≤ 5, not stretched | | | | | |")
                continue
            sm = R.get(f"extra|{j}_{b}|judge itself can't solve") or {}
            smt = f"{f(sm.get('x4'), ci=False)} / {f(sm.get('x11'), ci=False)}" if sm else "–"
            v1 = o.get("chosen_v1")
            L.append(f"| {BN[b]} | {nm} | {o['gap']:+.1f} | {o['layer']}{'' if o['status'] == 'responds' else '*'}"
                     f" ({v1 if v1 is not None else '–'}) | {o['sensitivity']:.2f} | {f(o.get('all | x11'))} | "
                     f"{f(o.get('not solved | x11'))} | {smt} | {o['all | random x11']['g']:+.1f} |")
    return "\n".join(L)


DIAG = """Three checks on each failing case: (i) the within-question correlation between the direction and the unedited verdict score; (ii) the same push applied at every token instead of only the last; (iii) how much of the direction's spread within a question is explained by which model wrote the answer.

- **Layer too early** (Llama-3.1-8B on MATH, layers ≤ 14). The correlation is −0.5 to +0.3 at layers 2–14 and +0.67 to +0.90 from layer 16. At layers 10–14 a last-token push moves the accept rate by ≤ 2 points, but the same push at every token moves it by up to 16 (layer 14: 83% → 99%). The verdict rebuilds its decision from the answer tokens in later layers and overwrites a last-token edit. *Fix: the push test.*
- **Verdict reads the direction backwards** (Llama-3.2-3B on MMLU, layers ≥ 14). The correlation is negative at every layer (−0.2 to −0.65), and pushing toward "right" makes it reject (98% → 44%). Both Llamas accept only 79% of Nemotron's answers against 98–99% of the Qwens', although Nemotron is right 72% of the time and Qwen3.5-4B 43%. The direction says Nemotron-like answers tend to be right; the 3B's verdict says the opposite. On MATH and BBEH the same judge responds normally (+6.4, +4.7). *No fix at those layers; the rule falls back to layer 12 (+4.0).*
- **Saturated verdict** (Mistral-7B on MMLU). It accepts 99% of answers with an average verdict score of +16.5 (odds about 10⁷ to 1). From layer 18 the verdict follows the direction (correlation +0.54 to +0.85) and pushes move the score (sensitivity 0.05–0.31), but never across zero, so the accept-rate check sees nothing. Stretching at layers 16–30 gains +2.3 to +3.6. *Fix: measure the response on the verdict score.* A score-based rule (sensitivity ≥ 0.05, then best *knows*) picks layer 16 (+2.3 [+0.5, +3.7]), and picks the same layer as the original rule wherever that rule worked. It was found after seeing this failure, so it still needs a fresh test.
- **The gain is authorship, not checking** (most not-solved gains on MMLU). 75–88% of the direction's spread within a question is explained by the answering model, at every layer, for every judge checked. *This is what the same-model test (section 4) controls for.*"""

SENS_TXT = """*Sensitivity* = how far the verdict score moves per 1 sd pushed along the direction, in units of the score's spread within a question (label-free, from the push test). Gains on all pairs; the less the verdict responds, the harder it needs to be stretched.

{t}

- High sensitivity (≥ 0.2): ×21 overshoots; use ×4–×11.
- Low sensitivity (< 0.08, mostly BBEH): ×11–×21.
- ×11 is within about 2 points of the best tested strength for most pairs, so it is a safe default. On same-model pairs, small judges need the gentler end (section 4)."""

if __name__ == "__main__":
    p = HERE / "report_2026-11-16-stretch-recipe.md"
    tmpl = HERE / "report_2026-11-16-stretch-recipe.template.md"
    if not tmpl.exists():
        tmpl.write_text(p.read_text())
    s = tmpl.read_text()
    s = (s.replace("TABLE_MAIN", main_table()).replace("TABLE_SM", sm_table()).replace("DIAG", DIAG)
         .replace("SENS", SENS_TXT.format(t=sens_table())).replace("FRESH_TABLE", fresh_table()))
    p.write_text(s)
    print(p)
