"""The tension (Nov 16): judges approve the wrong answers they believe (behaviour), yet the judge's "right minus wrong"
direction looked unrelated to the generate role's. Is the verdict-side axis really an "agrees with me" axis?

Belief per benchmark:
  rb2math  the anchoring study's belief (7 own answers per question, belief_rows_clean.json); believed = >= 4/7
           (only ~10 believed wrong answers per judge: too few on its own)
  bff      the same (anchoring study, 7 own answers); believed = >= 4/7
  bbeh     the model's own 5 thinking-off answers per question (out/solves_<key>.jsonl), exact match on the
           normalised final answer; believed = >= half of its answers; the model's own pool answers left out
For Qwen3.5-9B and Qwen3.6-35B-A3B. Per role (J judge, G end of answer, S self-check,
N neutral "FINAL:") and layer:

  1. Correctness axis vs belief, among WRONG answers: project each wrong answer on the role's own question-centred
     right-minus-wrong direction (learned on the other half of the questions), and ask how well that score ranks
     believed wrong answers (>= 4/7) above never-reached ones (0/7). AUROC 0.5 = the axis ignores belief; high = the
     axis treats "I would say this" as "right".
  2. Belief readable at all: a cross-validated probe for believed vs never-reached among wrong answers (whole
     questions held out), per role.
  3. Cosine between the belief direction (believed minus never-reached wrong answers) and each role's correctness
     direction.

  python3 experiments/beyond_capability/dir_belief.py --key qwen3.5-9b --tags main,neutral
  python3 experiments/beyond_capability/dir_belief.py --key qwen3.6-35b-a3b --tags roles4a,roles4b
      -> out_dirs/belief_dirs_<key>.md
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
ANC = HERE.parent / "anchoring_early_answer"
sys.path.insert(0, str(HERE))
from dir_analyze import center, cos, dom, load, probe_cv  # noqa: E402

ROLES = ["J", "G", "S", "N"]
NAMES = {"J": "judge (VERDICT:)", "G": "generate (end of answer)", "S": "self-check (VERDICT:)", "N": "neutral (FINAL:)"}


def halves(q, seed=0):
    u = sorted(set(q))
    rng = np.random.default_rng(seed)
    h = set(rng.permutation(u)[: len(u) // 2])
    return np.array([x in h for x in q])


def auc(y, s):
    y, s = np.asarray(y), np.asarray(s)
    return float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else float("nan")


def beliefs(key, bench):
    """aid -> (belief share, threshold for 'believed')."""
    if bench in ("rb2math", "bff"):
        return {r["item"]: r["belief"] for r in json.load(open(ANC / "out" / "belief_rows_clean.json"))
                if r["judge"] == key and r["bench"] == bench}, 4 / 7
    import importlib.util
    from bc_load import OUT, candidates, jl
    spec = importlib.util.spec_from_file_location("anc_analyze", ANC / "analyze.py")
    anc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(anc)
    own = {r["qid"]: [anc.norm(s["text"]) for s in r["samples"]] for r in jl(OUT / f"solves_{key}.jsonl")}
    out = {}
    for cid, c in candidates().items():
        a, o = anc.norm(c["answer"]), [v for v in own.get(c["qid"], []) if v is not None]
        if a is not None and len(o) >= 3 and c["examinee"] != key:
            out[cid] = sum(v == a for v in o) / len(o)
    return out, 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--tags", required=True)
    a = ap.parse_args()
    parts = [load(a.key, t) for t in a.tags.split(",")]
    L = []
    for bench in ("rb2math", "bff", "bbeh"):
        if any(m["bench"] == bench for _, meta, _ in parts for m in meta):
            L += run_bench(a.key, bench, parts)
    out = HERE / "out_dirs" / f"belief_dirs_{a.key}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("wrote", out)


def run_bench(key, bench, parts):
    belief, thr = beliefs(key, bench)
    layers = parts[0][2]
    rows = {}
    for H, meta, _ in parts:
        for i, m in enumerate(meta):
            if m["bench"] == bench and m["mode"] in ROLES and m["src"] != key:
                rows.setdefault(m["mode"], {})[m["aid"]] = (H, i, m)
    have = [r for r in ROLES if r in rows]
    aids = sorted(set.intersection(*[set(rows[r]) for r in have]))
    y = np.array([rows[have[0]][x][2]["gold"] for x in aids])
    q = np.array([rows[have[0]][x][2]["qid"] for x in aids])
    b = np.array([belief.get(x, np.nan) for x in aids], float)
    wrong = (y == 0) & ~np.isnan(b)
    bel = np.where(b >= thr - 1e-9, 1, np.where(b == 0, 0, -1))  # 1 believed, 0 never reached, -1 in between
    sel = wrong & (bel >= 0)
    L = [f"# Belief vs correctness axes: {key}, {bench}\n",
         f"{len(aids)} answers ({int((y == 1).sum())} right). Wrong answers with a belief score: {int(wrong.sum())}; "
         f"believed (>= {thr:.2f}): {int((sel & (bel == 1)).sum())}, never reached (0): {int((sel & (bel == 0)).sum())}.\n",
         "## 1. Does each role's correctness axis score believed WRONG answers as more 'right'?\n",
         "AUROC of the projection on the role's own right-minus-wrong direction (learned on the other half of the "
         "questions), believed vs never-reached wrong answers. 0.5 = ignores belief; > 0.5 = treats belief as rightness. "
         "Same axis, right vs wrong answers (all), for reference.\n",
         "| layer | " + " | ".join(f"{r}: belief / right-vs-wrong" for r in have) + " |", "|---|" + "---|" * len(have)]
    h = halves(q)
    best = {r: (0, -1) for r in have}
    for li, layer in enumerate(layers):
        cells = []
        for r in have:
            X = np.stack([rows[r][x][0][rows[r][x][1], li] for x in aids]).astype(np.float32)
            Xc = center(X, q)
            s = np.zeros(len(y))
            for tr, te in ((h, ~h), (~h, h)):  # direction from one half of the questions, scored on the other
                s[te] = Xc[te] @ dom(Xc[tr], y[tr])
            ab, ac = auc(bel[sel], s[sel]), auc(y, s)
            cells.append(f"{ab:.2f} / {ac:.2f}")
            if ac > best[r][1]:
                best[r] = (li, ac)
        L.append(f"| {layer} | " + " | ".join(cells) + " |")
    L += ["", "## 2. Is belief readable in each role? (probe, believed vs never-reached wrong answers)\n",
          "| role | layer (role's best right-vs-wrong) | probe AUROC | cosine(belief dir, own correctness dir) | "
          "cosine(belief dir, judge correctness dir) |", "|---|---|---|---|---|"]
    XJ = None
    if "J" in have:
        lj = best["J"][0]
        XJ = center(np.stack([rows["J"][x][0][rows["J"][x][1], lj] for x in aids]).astype(np.float32), q)
    for r in have:
        li = best[r][0]
        X = np.stack([rows[r][x][0][rows[r][x][1], li] for x in aids]).astype(np.float32)
        Xc = center(X, q)
        p = probe_cv(X[sel], bel[sel], q[sel])
        ok = ~np.isnan(p)
        bdir = dom(Xc[sel], bel[sel])
        cj = cos(dom(center(np.stack([rows[r][x][0][rows[r][x][1], best["J"][0]] for x in aids]).astype(np.float32), q)[sel],
                     bel[sel]), dom(XJ, y)) if XJ is not None else float("nan")
        L.append(f"| {r} {NAMES[r]} | {layers[li]} | {auc(bel[sel][ok], p[ok]):.2f} | {cos(bdir, dom(Xc, y)):+.2f} | {cj:+.2f} |")

    # 3. (Nov 16 rigor check) noise ceilings, and a control for a general "lean toward CORRECT": in the verdict roles,
    # the lean direction = answers the model's own verdict leans CORRECT on minus INCORRECT (margin sign). Project it
    # out of the states, then recompute belief and correctness directions and their cosine.
    L += ["", "## 3. Ceilings and the verdict-lean control (each role's best layer)\n",
          "Ceiling = cosine of the same direction built on two random halves of the questions. Lean = the model's own "
          "verdict lean (CORRECT minus INCORRECT by its margin); only roles that give a verdict have one.\n",
          "Disjoint = belief direction from one half of the questions vs correctness direction from the other half (and "
          "the reverse, averaged): no answers shared, so shared never-reached answers cannot inflate it.\n",
          "| role | cos(belief, correctness) | **disjoint halves** | ceiling belief | ceiling correctness | cos(belief, lean) | "
          "cos(correctness, lean) | cos(belief, correctness) with lean removed |", "|---|---|---|---|---|---|---|---|"]
    for r in have:
        li = best[r][0]
        Xc = center(np.stack([rows[r][x][0][rows[r][x][1], li] for x in aids]).astype(np.float32), q)
        bdir, cdir = dom(Xc[sel], bel[sel]), dom(Xc, y)
        hs = halves(q[sel], seed=1)
        cb = cos(dom(Xc[sel][hs], bel[sel][hs]), dom(Xc[sel][~hs], bel[sel][~hs]))
        hc = halves(q, seed=1)
        cc = cos(dom(Xc[hc], y[hc]), dom(Xc[~hc], y[~hc]))
        sa, sb = sel & hc, sel & ~hc
        dj = np.mean([cos(dom(Xc[sa], bel[sa]), dom(Xc[~hc], y[~hc])), cos(dom(Xc[sb], bel[sb]), dom(Xc[hc], y[hc]))])
        m = np.array([rows[r][x][2].get("margin") if rows[r][x][2].get("margin") is not None else np.nan for x in aids], float)
        if np.isfinite(m).sum() > 50:
            ok = np.isfinite(m)
            lean = dom(Xc[ok], (m[ok] > 0).astype(int))
            Xr = Xc - np.outer(Xc @ lean, lean)
            rest = cos(dom(Xr[sel], bel[sel]), dom(Xr, y))
            L.append(f"| {r} {NAMES[r]} | {cos(bdir, cdir):+.2f} | **{dj:+.2f}** | {cb:.2f} | {cc:.2f} | {cos(bdir, lean):+.2f} | "
                     f"{cos(cdir, lean):+.2f} | {rest:+.2f} |")
        else:
            L.append(f"| {r} {NAMES[r]} | {cos(bdir, cdir):+.2f} | **{dj:+.2f}** | {cb:.2f} | {cc:.2f} | – | – | – |")
    return L + [""]


if __name__ == "__main__":
    main()
