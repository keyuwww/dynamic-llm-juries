"""Score every (judge, benchmark) pair under the fixed layer rule (out_allpairs/RULE.md).

Per pair: GAP (best-layer KNOWS - SAYS), the chosen layer and whether any layer responds, the verdict's response at the
chosen layer (accept rate at -8 / +8 sd, all answers), and the ranking gain from stretching (x11 primary; x4, x21
secondary; random direction x11 as control), on all pairs / solved / not solved / same-model pairs (right vs wrong
answers written by the same answering model, which removes "who wrote it"). Gain = within-question AUROC after minus
unedited, x100; 95% CI from 1000 resamples of questions, paired.

Inputs: out_allpairs/<judge>_<bench>/{choice,final,meta}_<bench>.jsonl from allpairs_modal.py; the two pairs run
earlier as full layer sweeps (Llama-3.1-8B MATH, Llama-3.2-3B MMLU) are read from their sweep files at the layer the
same rule picks. Solve labels: see labels().

  python3 experiments/beyond_capability/allpairs_analyze.py -> out_allpairs/allpairs.md, allpairs.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
from bc_load import OUT, jl, questions, solve_stats  # noqa: E402
from data import bbeh_correct  # noqa: E402
from stretch_analyze import solve_labels  # noqa: E402

D = HERE / "out_allpairs"
JUDGES = ["llama3.1-8b", "llama3.2-3b", "qwen3.5-9b", "qwen3.5-4b", "phi4-mini", "mistral-7b", "granite3.3-8b"]
NAME = {"llama3.1-8b": "Llama-3.1-8B", "llama3.2-3b": "Llama-3.2-3B", "qwen3.5-9b": "Qwen3.5-9B",
        "qwen3.5-4b": "Qwen3.5-4B", "phi4-mini": "Phi-4-mini", "mistral-7b": "Mistral-7B", "granite3.3-8b": "Granite-3.3-8B"}
BENCHES = ["mmlu", "math", "bbeh"]
BNAME = {"mmlu": "MMLU-Redux", "math": "MATH", "bbeh": "BBEH"}
KNOWN_SMALL = {("qwen3.5-9b", "mmlu"): 0.8, ("qwen3.5-9b", "math"): 4.9, ("qwen3.5-9b", "bbeh"): -1.5,
               ("qwen3.5-4b", "mmlu"): 1.2}  # gaps measured earlier (screen / stretch runs), all <= 5
J11, J4, J21, R11, M8, P8 = ("Jc:amplify:10.0", "Jc:amplify:3.0", "Jc:amplify:20.0", "Rc:amplify:10.0",
                             "Jc:add:-8.0", "Jc:add:8.0")


def labels(judge, bench):
    """qid -> 1 if the judge solved the question itself (thinking off), else 0."""
    if bench == "mmlu":
        return solve_labels("mmlu_full", judge, HERE / "out_mmlu")
    if bench == "math":
        return solve_labels("math_full", judge, HERE / "out_math" if judge == "llama3.1-8b" else OUT)
    qs = questions()
    if judge == "qwen3.5-4b":
        return {q: s["maj_ok"] for q, s in solve_stats(jl(OUT / "solves_qwen3.5-4b.jsonl"), qs).items()}
    if judge == "llama3.1-8b":
        return {r["qid"]: int(bbeh_correct(r["answer"] or "", qs[r["qid"]]["target"]))
                for r in jl(HERE.parent / "anchoring_early_answer" / "out_llama" / "solves.jsonl")
                if r["bench"] == "bbeh" and str(r["clean"]) == "True"}
    f = D / f"{judge}_bbeh" / f"esolves_bbeh_{judge}.jsonl"
    return {r["qid"]: 0 if r.get("capped") else int(bbeh_correct(r["text"], qs[r["qid"]]["target"])) for r in jl(f)} \
        if f.exists() else {}


def place_solves():
    """copy the judges' own answers from out_allpairs/ to where the label readers expect them."""
    import shutil
    for f in D.glob("*/esolves_*.jsonl"):
        bench, judge = f.stem.split("_", 2)[1:]
        dest = {"mmlu": HERE / "out_mmlu" / f"esolves_mmlu_full_{judge}.jsonl",
                "math": OUT / f"esolves_math_full_{judge}.jsonl"}.get(bench)
        if dest is not None and (not dest.exists() or dest.stat().st_size != f.stat().st_size):
            shutil.copy(f, dest)


def pooled(xs):
    """inverse-variance weighted mean of per-pair gains (SE from the 95% interval)."""
    xs = [x for x in xs if x and x["hi"] > x["lo"]]
    if not xs:
        return None
    w = np.array([1 / ((x["hi"] - x["lo"]) / 3.92) ** 2 for x in xs])
    g = np.array([x["g"] for x in xs])
    m, se = float((w * g).sum() / w.sum()), float(1 / np.sqrt(w.sum()))
    return dict(g=m, lo=m - 1.96 * se, hi=m + 1.96 * se, k=len(xs))


def per_q(rows, key, same_src=False):
    by = defaultdict(lambda: ([], []))
    for r in rows:
        by[(r["qid"], r["src"] if same_src else "")][r["gold"]].append(r["margins"][key])
    out = defaultdict(lambda: np.zeros(2))
    for (q, _), (neg, pos) in by.items():
        if pos and neg:
            a, b = np.array(pos)[:, None], np.array(neg)[None, :]
            out[q] += [(a > b).sum() + 0.5 * (a == b).sum(), a.size * b.size]
    return out


def gain(rows, key, same_src=False, n=1000):
    b, s = per_q(rows, "none", same_src), per_q(rows, key, same_src)
    qs = sorted(b)
    if len(qs) < 5:
        return None
    B, S = np.array([b[q] for q in qs]), np.array([s[q] for q in qs])
    g = lambda i: 100 * (S[i, 0].sum() / S[i, 1].sum() - B[i, 0].sum() / B[i, 1].sum())  # noqa: E731
    rng = np.random.default_rng(0)
    bs = [g(rng.integers(0, len(qs), len(qs))) for _ in range(n)]
    return dict(g=float(g(slice(None))), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                says=float(B[:, 0].sum() / B[:, 1].sum()), nq=len(qs))


def load_pair(judge, bench):
    """(choice dict, final rows with margins keyed as in pair_pipeline) or None."""
    if (judge, bench) == ("llama3.1-8b", "math") or (judge, bench) == ("llama3.2-3b", "mmlu"):
        d = HERE / ("out_math/layer_sweep" if bench == "math" else "out_mmlu/layer_sweep_llama3.2-3b")
        tag = bench
        sd = json.load(open(d / f"sweep_dirs_{tag}.json"))
        knows = {int(L): v["knows"] for L, v in sd["layers"].items()}
        rows = [json.loads(l) for f in sorted(d.glob(f"sweep_{tag}_L*.jsonl")) for l in open(f)]
        meta = [json.loads(l) for l in open(d / f"meta_{tag}.jsonl")]
        src = {m["aid"]: m["src"] for m in meta}
        push = {}
        for L in knows:
            J = [r for r in rows if r["layer"] == L and r["dir"] == "Jc"]
            push[L] = dict(minus8=100 * np.mean([r["margins"]["add:-8.0"] > 0 for r in J]),
                           plus8=100 * np.mean([r["margins"]["add:8.0"] > 0 for r in J]))
        resp = [L for L in knows if push[L]["plus8"] - push[L]["minus8"] >= 10]
        Lmax = max(knows, key=knows.get)
        chosen = max(resp, key=knows.get) if resp else Lmax
        says = gain([dict(r, src=src[r["aid"]]) for r in rows if r["layer"] == chosen and r["dir"] == "Jc"],
                    "amplify:10.0", n=1)["says"]
        choice = dict(knows=knows, says=says, gap=100 * (knows[Lmax] - says), best_knows_layer=Lmax, push=push,
                      responding_layers=sorted(resp), chosen_layer=chosen,
                      rule="responds" if resp else "no layer responds", source="full layer sweep")
        by = defaultdict(dict)
        for r in rows:
            if r["layer"] == chosen:
                m = r["margins"]
                by[r["aid"]].update({"none": m["none"]} | {f"{r['dir']}:{k}": v for k, v in m.items() if k != "none"})
                by[r["aid"]].update(_meta=dict(qid=r["qid"], gold=r["gold"], src=src[r["aid"]]))
        final = [dict(v.pop("_meta"), margins=v) for v in by.values()]
        return choice, final
    d = D / f"{judge}_{bench}"
    f = d / f"choice_{bench}.json"
    if not f.exists():
        return None
    choice = json.load(open(f))
    choice["knows"] = {int(k): v for k, v in choice["knows"].items()}
    if "push" in choice:
        choice["push"] = {int(k): v for k, v in choice["push"].items()}
    ff = d / f"final_{bench}.jsonl"
    return choice, ([json.loads(l) for l in open(ff)] if ff.exists() else None)


def fmt(x):
    return "–" if x is None else f"{x['g']:+.1f} [{x['lo']:+.1f}, {x['hi']:+.1f}]"


def main():
    place_solves()
    res, lines = {}, []
    for bench in BENCHES:
        for judge in JUDGES:
            if (judge, bench) in KNOWN_SMALL:
                res[f"{judge}|{bench}"] = dict(gap=KNOWN_SMALL[(judge, bench)], status="gap <= 5 (measured earlier)")
                continue
            p = load_pair(judge, bench)
            if p is None:
                res[f"{judge}|{bench}"] = dict(status="not run / pending")
                continue
            choice, final = p
            out = dict(gap=choice["gap"], says=choice["says"], best_knows=max(choice["knows"].values()),
                       best_knows_layer=choice["best_knows_layer"])
            if "stopped" in choice or final is None:
                out["status"] = choice.get("stopped", "no final pass")
                res[f"{judge}|{bench}"] = out
                continue
            sol = labels(judge, bench)
            L = choice["chosen_layer"]
            out.update(status=choice["rule"], layer=L, n_layers=choice.get("n_layers"), knows_at_layer=choice["knows"][L],
                       responding=choice["responding_layers"], push_at_layer=choice["push"][L],
                       n_answers=len(final), n_solve_labels=len(sol),
                       accept_m8=100 * np.mean([r["margins"][M8] > 0 for r in final]),
                       accept_p8=100 * np.mean([r["margins"][P8] > 0 for r in final]),
                       accept_none=100 * np.mean([r["margins"]["none"] > 0 for r in final]))
            groups = {"all": final, "solved": [r for r in final if sol.get(r["qid"]) == 1],
                      "not solved": [r for r in final if sol.get(r["qid"]) == 0]}
            for gname, R in groups.items():
                for key, tag in ((J11, "x11"), (J4, "x4"), (J21, "x21"), (R11, "random x11")):
                    if R and key in R[0]["margins"]:
                        out[f"{gname} | {tag}"] = gain(R, key)
                        out[f"{gname} | {tag} | same-model"] = gain(R, key, same_src=True)
            res[f"{judge}|{bench}"] = out
    json.dump(res, open(D / "allpairs.json", "w"), indent=1)
    lines += ["# Stretching the judge direction at a rule-chosen layer: every judge × benchmark", "",
              "Ranking = within-question AUROC (right answer scored above a wrong answer to the same question; 0.50 = "
              "coin flip). Gap = 100 × (best layer's direction ranking − verdict ranking). Gain = ranking change × 100 "
              "after stretching ×11 at the chosen layer [95% CI, questions resampled]. Same-model = only right-vs-wrong "
              "pairs written by the same answering model. Rule: out_allpairs/RULE.md.", "",
              "| Benchmark | Judge | Gap | Layer (rule) | Accept −8 → +8 sd | Gain ×11, all | Not solved | "
              "Same-model, not solved | Same-model, solved | Random ×11 | Best of ×4/×11/×21 (all) |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for bench in BENCHES:
        for judge in JUDGES:
            o = res[f"{judge}|{bench}"]
            head = f"| {BNAME[bench]} | {NAME[judge]} | {o['gap']:+.1f} |" if "gap" in o else f"| {BNAME[bench]} | {NAME[judge]} | – |"
            if "layer" not in o:
                lines.append(head + f" {o['status']} | | | | | | | |")
                continue
            best = max(("x4", "x11", "x21"), key=lambda t: (o.get(f"all | {t}") or {"g": -99})["g"])
            lines.append(head + f" {o['layer']}/{o['n_layers']} ({'responds' if o['status'] == 'responds' else 'none responds'}) | "
                         f"{o['accept_m8']:.0f}% → {o['accept_p8']:.0f}% | {fmt(o.get('all | x11'))} | "
                         f"{fmt(o.get('not solved | x11'))} | {fmt(o.get('not solved | x11 | same-model'))} | "
                         f"{fmt(o.get('solved | x11 | same-model'))} | {(o.get('all | random x11') or {'g': float('nan')})['g']:+.1f} | "
                         f"{best}: {fmt(o.get(f'all | {best}'))} |")
    ok = [o for o in res.values() if o.get("layer") is not None]
    resp = [o for o in ok if o["status"] == "responds"]
    lines += ["", "**Pooled over pairs** (inverse-variance weighted; pairs are not independent draws, so read as a summary):", "",
              "| Pairs | k | Gain ×11, all | Not solved | Same-model, not solved | Same-model, solved |", "|---|---|---|---|---|---|"]
    for name, P in (("rule found a responding layer", resp), ("all pairs with gap > 5", ok)):
        cells = [pooled([o.get(k) for o in P]) for k in ("all | x11", "not solved | x11", "not solved | x11 | same-model",
                                                         "solved | x11 | same-model")]
        lines.append(f"| {name} | {len(P)} | " + " | ".join(fmt(c) for c in cells) + " |")
    ext = sorted(D.glob("*/extra_*.jsonl"))
    if ext:
        lines += ["", "## Same-model test: many right and wrong answers from one model (Qwen3.5-4B), questions the judge can't solve", "",
                  "All pairs compare a right and a wrong answer written by the same model, so \"who wrote it\" cannot help. "
                  "Gain = ranking change × 100 [95% CI, questions resampled].", "",
                  "| Pair | Layer | Questions | Answers | Verdict ranking before | ×4 | ×11 | ×21 | Random ×11 |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for f in ext:
            R = [json.loads(l) for l in open(f)]
            g = {t: gain(R, k) for t, k in (("x4", J4), ("x11", J11), ("x21", J21), ("r", R11))}
            res[f"extra|{f.parent.name}"] = g
            lines.append(f"| {f.parent.name} | {R[0]['layer']} | {g['x11']['nq']} | {len(R)} | {g['x11']['says']:.3f} | "
                         f"{fmt(g['x4'])} | {fmt(g['x11'])} | {fmt(g['x21'])} | {g['r']['g']:+.1f} |")
        json.dump(res, open(D / "allpairs.json", "w"), indent=1)
    diag = sorted(D.glob("*/diag_*.json"))
    if diag:
        lines += ["", "## Why a verdict does or doesn't respond (diagnostics)", "",
                  "corr = within-question correlation of the direction with the unedited verdict margin; "
                  "src share = share of the direction's within-question spread explained by which model wrote the answer; "
                  "push = accept rate at −8 → +8 sd, edit at the last token vs at every token.", ""]
        for f in diag:
            g = json.load(open(f))
            lines += [f"### {f.parent.name}", "", "| Layer | corr | src share | push, last token | push, every token |",
                      "|---|---|---|---|---|"]
            for L, v in sorted(g.items(), key=lambda kv: int(kv[0])):
                lines.append(f"| {L} | {v['corr']:+.2f} | {v['src_share']:.2f} | {v['push_last'][0]:.0f}% → {v['push_last'][1]:.0f}% | "
                             f"{v['push_all'][0]:.0f}% → {v['push_all'][1]:.0f}% |")
            lines.append("")
    (D / "allpairs.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
