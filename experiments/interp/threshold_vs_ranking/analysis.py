#!/usr/bin/env python3
"""
Threshold vs ranking: is the "interior layer beats the final verdict" gain a better RANKING of
items, or just a better CUTOFF on the final layer's score?

CPU-only, reads only existing per-item per-layer logit-lens scores
(experiments/interp/logit_lens_results/*/pilot_results.json). Nothing is re-run on a GPU.

Protocol (reproduces experiments/interp/held_out_significance.py exactly, then adds columns):
  * Python random.Random(seed=0), one list of item indices shuffled IN PLACE once per split,
    first floor(n/2) items = half A, rest = half B; 200 splits. Same split sequence as the
    original, so (c) - (a) below reproduces the saved `all_gaps` split for split.
  * On A: best layer = argmax over ALL layer indices (0 = embeddings ... last = final hidden
    state) of Cohen's kappa of the argmax verdict (P(pos) >= 0.5) vs gold; first index wins ties
    (same as original). ALSO on A: fit a cutoff t on the FINAL layer's score
    s = P(pos | two-way renormalised), i.e. predict pos iff s > t, choosing t to maximise kappa
    on A (t placed at the midpoint between adjacent distinct scores; ties in kappa broken toward
    the cutoff closest to 0.5 in log-odds).
  * On B:  (a) final verdict as recorded by the original run (pred field; original baseline)
           (a') final-layer lens score at 0.5 (sanity: should match (a) closely)
           (b) final-layer score with the cutoff fitted on A ("recalibrated final")
           (c) chosen layer, argmax verdict (original "interior layer")
           (d) AUROC of the final-layer score and of the chosen layer's score.
    P(pos) is a monotone function of the logit margin (it is sigmoid(logit_pos - logit_neg)),
    so AUROC and the fitted cutoff are identical whichever of the two is used.

Per cell: gain = (c)-(a); recovered share = mean((b)-(a)) / mean((c)-(a)) (ratio of means;
a per-split ratio is unstable when the per-split gain is near zero); AUROC gain = AUROC(chosen)
- AUROC(final). Intervals: 2.5-97.5 percentiles of the per-split values over the 200 splits
(split-to-split spread; this is what a fresh half-size test set would show). For "is there a
gain at all" we use the original script's criterion (bootstrap-over-splits 95% CI of the mean
gap excludes 0) plus a materiality floor of 0.02 kappa.

Verdict per cell:
  no gain        : mean gain < 0.02 kappa, or bootstrap CI of the mean gap includes 0
  mostly cutoff  : gain, and recalibrating the final layer recovers >= 70% of it
  mostly ranking : gain, recalibration recovers < 30%, and AUROC gain >= 0.02
  neither        : gain, recalibration recovers < 30%, but AUROC gain < 0.02 (unexplained)
  mixed          : gain, recovery between 30% and 70%

Usage: python analysis.py   (writes results.md and results.json next to this file)
"""
import glob
import json
import random
import re
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
INTERP = HERE.parent
N_SPLITS = 200
SEED = 0
GAIN_FLOOR = 0.02
CUTOFF_SHARE = 0.70
RANKING_SHARE = 0.30


# ----------------------------------------------------------------------------- metrics
def kappa_vec(gold, preds):
    """Cohen's kappa of each column of `preds` (n x L, 0/1) vs `gold` (n,), computed with the
    same float operations as held_out_significance.kappa so layer choices tie-break identically."""
    n = len(gold)
    po = (preds == gold[:, None]).sum(axis=0) / n
    p1 = gold.sum() / n
    p2 = preds.sum(axis=0) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    with np.errstate(divide="ignore", invalid="ignore"):
        k = (po - pe) / (1 - pe)
    return np.where(pe >= 0.999999, 1.0, k)


def kappa1(gold, pred):
    return float(kappa_vec(gold, pred[:, None])[0])


def auroc(gold, score):
    pos = gold == 1
    npos, nneg = pos.sum(), (~pos).sum()
    if npos == 0 or nneg == 0:
        return float("nan")
    r = rankdata(score)
    return float((r[pos].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def logit(p):
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return np.log(p / (1 - p))


def fit_cutoff(gold, s):
    """Cutoff t maximising kappa of (s > t) vs gold. Returns t (float, may be +-inf)."""
    order = np.argsort(-s, kind="mergesort")
    ss, yy = s[order], gold[order]
    n = len(ss)
    npos = yy.sum()
    tp = np.concatenate([[0], np.cumsum(yy)])          # TP when top-k predicted positive
    k = np.arange(n + 1)
    # valid boundaries: k = 0, k = n, or a strict drop between ss[k-1] and ss[k]
    valid = np.ones(n + 1, bool)
    valid[1:n] = ss[:-1] > ss[1:]
    k, tp = k[valid], tp[valid]
    po = (tp + (n - npos - (k - tp))) / n
    p1 = npos / n
    p2 = k / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    with np.errstate(divide="ignore", invalid="ignore"):
        kap = np.where(pe >= 0.999999, 1.0, (po - pe) / (1 - pe))
    thr = np.empty(len(k))
    for j, kk in enumerate(k):
        if kk == 0:
            thr[j] = np.inf
        elif kk == n:
            thr[j] = -np.inf
        else:
            thr[j] = 0.5 * (ss[kk - 1] + ss[kk])
    best = np.flatnonzero(np.isclose(kap, kap.max(), rtol=0, atol=1e-12))
    dist = np.abs(logit(np.clip(thr[best], 0, 1)))  # +-inf thresholds -> far from 0.5
    dist[~np.isfinite(thr[best])] = np.inf
    return float(thr[best[np.argmin(dist)]])


# ----------------------------------------------------------------------------- cells
def final_pred_binary(v, label_pos="CORRECT"):
    if isinstance(v, (int, bool)):
        return int(bool(v))
    return 1 if str(v) == label_pos else 0


def discover_cells():
    cells, skipped = [], []
    # main 42: exactly the cells that have a saved held-out significance result
    sig_files = sorted(glob.glob(str(INTERP / "significance_results" / "*.json")))
    for f in sig_files:
        sig = json.loads(Path(f).read_text())
        name = Path(f).stem
        pilot = sig["pilot"].split(" ")[0]
        bench = name.split("_")[0]
        group = "main" if bench in ("bff", "biggen", "healthbench") else "supplementary"
        cells.append(dict(name=name, group=group, pilot=pilot, pcn=sig["pcn_field"],
                          pred=sig["pred_field"], sig_file=f))
    have = {(c["pilot"], c["pcn"]) for c in cells}
    # supplementary: RB2-Safety / JudgeBench runs without a saved significance file
    for p in sorted(glob.glob(str(INTERP / "logit_lens_results" / "*" / "pilot_results.json"))):
        d = Path(p).parent.name
        m = re.match(r"(judgebench|rb2safety_rubric|rb2safety)_(.+)$", d)
        if not m:
            continue
        rel = str(Path(p).relative_to(INTERP))
        if (rel, "pcn") in have:
            continue
        bench, model = m.groups()
        tag = {"judgebench": "judgebench", "rb2safety": "rb2safety_standard",
               "rb2safety_rubric": "rb2safety_rubric"}[bench]
        pred = "final_pred_a" if bench == "judgebench" else "final_pred_correct"
        cells.append(dict(name=f"{tag}_{model}", group="supplementary", pilot=rel, pcn="pcn",
                          pred=pred, sig_file=None))
    return cells, skipped


def model_of(name):
    for b in ("bff_rubric_", "bff_standard_", "biggen_rubric_", "biggen_standard_",
              "healthbench_rubric_", "healthbench_standard_", "rb2safety_rubric_",
              "rb2safety_standard_", "judgebench_"):
        if name.startswith(b):
            return b.rstrip("_"), name[len(b):]
    return "?", name


def run_cell(cell):
    pilot = json.loads((INTERP / cell["pilot"]).read_text())
    items = [it for it in pilot["items"] if it.get(cell["pcn"]) is not None]
    if not items:
        return None, (f"no `{cell['pcn']}` field in {cell['pilot']} (only "
                      f"{sorted(pilot['items'][0].keys())})")
    gold = np.array([it["gold"] for it in items], dtype=np.int64)
    S = np.array([it[cell["pcn"]] for it in items], dtype=np.float64)   # n x L
    final_pred = np.array([final_pred_binary(it[cell["pred"]]) for it in items], dtype=np.int64)
    n, L = S.shape
    P = (S >= 0.5).astype(np.int64)
    sF = S[:, -1]

    rng = random.Random(SEED)
    idx = list(range(n))
    rec = {k: [] for k in ("a", "a_lens", "b", "c", "auc_final", "auc_chosen", "layer", "cut")}
    for _ in range(N_SPLITS):
        rng.shuffle(idx)
        half = n // 2
        A = np.array(idx[:half]); B = np.array(idx[half:])
        kA = kappa_vec(gold[A], P[A])
        Lstar = int(np.argmax(kA))
        t = fit_cutoff(gold[A], sF[A])
        gB = gold[B]
        rec["a"].append(kappa1(gB, final_pred[B]))
        rec["a_lens"].append(kappa1(gB, P[B, -1]))
        rec["b"].append(kappa1(gB, (sF[B] > t).astype(np.int64)))
        rec["c"].append(kappa1(gB, P[B, Lstar]))
        rec["auc_final"].append(auroc(gB, sF[B]))
        rec["auc_chosen"].append(auroc(gB, S[B, Lstar]))
        rec["layer"].append(Lstar)
        rec["cut"].append(t)
    r = {k: np.array(v, dtype=float) for k, v in rec.items()}

    gain = r["c"] - r["a"]
    recov = r["b"] - r["a"]
    dauc = r["auc_chosen"] - r["auc_final"]

    # reproduction check against the saved significance file
    repro = None
    if cell["sig_file"]:
        saved = np.array(json.loads(Path(cell["sig_file"]).read_text())["all_gaps"])
        repro = float(np.max(np.abs(saved - gain))) if len(saved) == len(gain) else float("nan")

    # original-style "is there a gain" test: bootstrap CI (over splits) of the mean gap
    brng = np.random.default_rng(SEED)
    boots = gain[brng.integers(0, N_SPLITS, size=(10000, N_SPLITS))].mean(axis=1)
    boot_lo, boot_hi = np.percentile(boots, [2.5, 97.5])
    mg, mr = gain.mean(), recov.mean()
    share = mr / mg if mg > 0 else float("nan")
    # bootstrap-over-splits interval for the share (ratio of means); narrow by construction
    sh_boot = []
    for row in brng.integers(0, N_SPLITS, size=(2000, N_SPLITS)):
        g = gain[row].mean()
        if g > 0:
            sh_boot.append(recov[row].mean() / g)
    sh_lo, sh_hi = (np.percentile(sh_boot, [2.5, 97.5]) if len(sh_boot) > 100 else (np.nan, np.nan))

    if mg < GAIN_FLOOR or boot_lo <= 0:
        verdict = "no gain"
    elif share >= CUTOFF_SHARE:
        verdict = "mostly cutoff"
    elif share < RANKING_SHARE and dauc.mean() >= GAIN_FLOOR:
        verdict = "mostly ranking"
    elif share < RANKING_SHARE:
        verdict = "neither"   # recalibration doesn't recover it, but AUROC doesn't improve either
    else:
        verdict = "mixed"

    pc = lambda x: [float(v) for v in np.percentile(x, [2.5, 97.5])]
    bench, model = model_of(cell["name"])
    modal = int(np.bincount(r["layer"].astype(int)).argmax())
    return dict(
        cell=cell["name"], group=cell["group"], bench=bench, model=model, pilot=cell["pilot"],
        n_items=int(n), n_layers=int(L), gold_pos_rate=float(gold.mean()),
        final_pos_rate=float(final_pred.mean()),
        final_pred_vs_lens_agree=float((final_pred == P[:, -1]).mean()),
        modal_layer=modal, modal_layer_depth_pct=100 * modal / (L - 1),
        frac_splits_chose_final_layer=float((r["layer"] == L - 1).mean()),
        median_cutoff=float(np.median(r["cut"][np.isfinite(r["cut"])])) if np.isfinite(r["cut"]).any() else None,
        kappa_a_final=float(r["a"].mean()), kappa_a_lens_final=float(r["a_lens"].mean()),
        kappa_b_recal=float(r["b"].mean()), kappa_c_layer=float(r["c"].mean()),
        gain=float(mg), gain_pi95=pc(gain), gain_mean_boot95=[float(boot_lo), float(boot_hi)],
        recovered=float(mr), recovered_pi95=pc(recov),
        share_recovered=float(share), share_boot95=[float(sh_lo), float(sh_hi)],
        share_from_lens_readout=float(r["a_lens"].mean() - r["a"].mean()) / mg if mg > 0 else float("nan"),
        resid_after_recal=float((r["c"] - r["b"]).mean()), resid_pi95=pc(r["c"] - r["b"]),
        auroc_final=float(r["auc_final"].mean()), auroc_chosen=float(r["auc_chosen"].mean()),
        auroc_gain=float(dauc.mean()), auroc_gain_pi95=pc(dauc),
        frac_splits_auroc_gain_pos=float((dauc > 0).mean()),
        repro_max_abs_diff_vs_saved_gaps=repro, verdict=verdict,
    ), None


# ----------------------------------------------------------------------------- report
SHORT = {"gpt-oss-120b": "gpt-oss-120b", "gpt-oss-20b": "gpt-oss-20b",
         "nvidia-nemotron-3-nano-30b-a3b-bf16": "nemotron3-nano-30b",
         "nvidia-nemotron-3-super-120b-a12b-bf16": "nemotron3-super-120b",
         "qwen3.5-4b": "qwen3.5-4b", "qwen3.5-9b": "qwen3.5-9b", "qwen3.6-35b-a3b": "qwen3.6-35b-a3b"}


def f(x, d=3, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def table(rows):
    hdr = ("| cell | n | layer (depth) | (a) final | (a') lens final @0.5 | (b) recal. final | (c) layer "
           "| gain (c-a) [95% over splits] | recovered by recal. | AUROC final | AUROC layer "
           "| AUROC gain [95% over splits] | verdict |")
    out = [hdr, "|" + "---|" * 13]
    for r in rows:
        share = "--" if r["verdict"] == "no gain" else f"{100 * r['share_recovered']:.0f}%"
        flag = "" if r["final_pred_vs_lens_agree"] >= 0.95 else " ‡"
        out.append(
            f"| {r['bench']} / {SHORT.get(r['model'], r['model'])}{flag} | {r['n_items']} "
            f"| {r['modal_layer']}/{r['n_layers'] - 1} ({r['modal_layer_depth_pct']:.0f}%) "
            f"| {f(r['kappa_a_final'])} | {f(r['kappa_a_lens_final'])} | {f(r['kappa_b_recal'])} | {f(r['kappa_c_layer'])} "
            f"| {f(r['gain'], sign=True)} [{f(r['gain_pi95'][0], 2, True)}, {f(r['gain_pi95'][1], 2, True)}] "
            f"| {share} | {f(r['auroc_final'])} | {f(r['auroc_chosen'])} "
            f"| {f(r['auroc_gain'], sign=True)} [{f(r['auroc_gain_pi95'][0], 2, True)}, {f(r['auroc_gain_pi95'][1], 2, True)}] "
            f"| **{r['verdict']}** |")
    return "\n".join(out)


def main():
    cells, _ = discover_cells()
    results, skipped = [], []
    for c in cells:
        res, why = run_cell(c)
        if res is None:
            skipped.append(dict(cell=c["name"], group=c["group"], reason=why))
            print(f"SKIP {c['name']}: {why}", flush=True)
        else:
            results.append(res)
            print(f"{res['cell']:<55} gain={res['gain']:+.3f} share={res['share_recovered']:+.2f} "
                  f"dAUC={res['auroc_gain']:+.3f} repro={res['repro_max_abs_diff_vs_saved_gaps']} "
                  f"-> {res['verdict']}", flush=True)

    order = {"bff": 0, "biggen": 1, "healthbench": 2, "rb2safety": 3, "judgebench": 4}
    key = lambda r: (r["model"], order.get(r["bench"].split("_")[0], 9), r["bench"])
    main_rows = sorted([r for r in results if r["group"] == "main"], key=key)
    sup_rows = sorted([r for r in results if r["group"] == "supplementary"], key=key)
    (HERE / "results.json").write_text(json.dumps(dict(
        n_splits=N_SPLITS, seed=SEED, gain_floor=GAIN_FLOOR, cutoff_share=CUTOFF_SHARE,
        ranking_share=RANKING_SHARE, results=main_rows + sup_rows, skipped=skipped), indent=1))

    def counts(rows):
        c = {}
        for r in rows:
            c.setdefault(r["verdict"], []).append(r)
        return c

    def models(rs):
        m = {}
        for r in rs:
            m[SHORT.get(r["model"], r["model"])] = m.get(SHORT.get(r["model"], r["model"]), 0) + 1
        return ", ".join(f"{k} ({v})" for k, v in sorted(m.items(), key=lambda kv: -kv[1]))

    cm = counts(main_rows)
    n_main = len(main_rows)
    repro = [r["repro_max_abs_diff_vs_saved_gaps"] for r in results if r["repro_max_abs_diff_vs_saved_gaps"] is not None]
    lines = []
    lines.append("# Interior-layer gain: better ranking or just a better cutoff?\n")
    lines.append("## Summary (plain English)\n")
    g = [r for r in main_rows if r["verdict"] != "no gain"]
    lines.append(f"- Of the {n_main} main cells with usable scores (7 judges x BFF/BiGGen/HealthBench x rubric/no rubric, minus {42 - n_main} skipped), "
                 f"{len(g)} show a real held-out gain from reading an interior layer; {len(cm.get('no gain', []))} show none.")
    lines.append(f"- **Mostly cutoff** (just moving the final layer's yes/no threshold, fitted on the other half, recovers >= 70% of the gain): "
                 f"{len(cm.get('mostly cutoff', []))} cells -- {models(cm.get('mostly cutoff', [])) or 'none'}.")
    lines.append(f"- **Mostly ranking** (re-thresholding the final layer recovers < 30%; the interior layer orders items better): "
                 f"{len(cm.get('mostly ranking', []))} cells -- {models(cm.get('mostly ranking', [])) or 'none'}.")
    nm = len(cm.get("neither", []))
    lines.append(f"- **Mixed** (30-70% recovered): {len(cm.get('mixed', []))} cells -- {models(cm.get('mixed', [])) or 'none'}"
                 + (f"; **neither** (< 30% recovered but no AUROC gain either): {nm} -- {models(cm['neither'])}" if nm else "") + ".")
    def mean_dauc(v):
        rs = cm.get(v, [])
        return f"{np.mean([r['auroc_gain'] for r in rs]):+.3f}" if rs else "n/a"
    lines.append("- AUROC (how well a score sorts good answers above bad ones, ignoring any threshold; 0.5 = chance, 1 = perfect) agrees: "
                 f"mean AUROC gain of the chosen layer over the final layer is {mean_dauc('mostly cutoff')} in 'mostly cutoff' cells, "
                 f"{mean_dauc('mixed')} in 'mixed' cells and {mean_dauc('mostly ranking')} in 'mostly ranking' cells. "
                 "Caveat for qwen3.5-4b: part of its 'gain' is already there in the final layer's own logit-lens readout at 0.5 "
                 "(column a' vs a; " + ", ".join(f"{r['bench']} {100 * r['share_from_lens_readout']:.0f}%" for r in main_rows
                                                  if r['model'] == 'qwen3.5-4b' and r['verdict'] != 'no gain')
                 + " of the gain), i.e. the lens and the recorded verdict disagree; the rest is the cutoff. Either way the interior layer adds no ranking there.\n")

    lines.append("## What was done\n")
    lines.append(f"Same split protocol as `experiments/interp/held_out_significance.py` (seed {SEED}, {N_SPLITS} random half/half splits, "
                 "layer chosen on half A by Cohen's kappa of the argmax verdict, scored on half B). "
                 f"Reproduction check: (c)-(a) matches the saved per-split gaps in `significance_results/*.json` to within "
                 f"{max(repro):.1e} (max abs difference over all splits of all {len(repro)} cells that have a saved file).\n")
    lines.append("On half A we also fit a single cutoff on the final layer's P(positive label) (two-way renormalised logit-lens "
                 "probability at the verdict position; monotone in the logit margin) to maximise kappa. On half B:\n")
    lines.append("- **(a) final** = the final verdict exactly as the original analysis used it (the run's recorded argmax prediction);")
    lines.append("- **(b) recal. final** = final-layer score with the cutoff fitted on A;")
    lines.append("- **(c) layer** = layer chosen on A, argmax verdict (P >= 0.5) -- the original 'interior layer';")
    lines.append("- **AUROC final / layer** = threshold-free ranking quality of the final-layer score / the chosen layer's score on B.\n")
    lines.append("Cohen's kappa = agreement with the human label corrected for chance (0 = no better than guessing from base rates, "
                 "1 = perfect). 'gain' = (c) - (a). 'recovered by recal.' = mean((b) - (a)) / mean((c) - (a)) -- the share of the "
                 "interior-layer gain you also get by keeping the final layer and only moving its threshold. "
                 "Brackets = 2.5-97.5 percentiles of the per-split values over the 200 splits (spread you would see on a fresh "
                 "half-size test set). A cell counts as 'gain' only if the mean gain >= 0.02 kappa and the original script's "
                 "bootstrap CI on the mean gap excludes 0. 'layer (depth)' = modal chosen layer index / last index "
                 "(index 0 = embeddings, last = final hidden state). Mean (a)/(b)/(c) are averages over the 200 B halves.\n")
    lines.append("‡ = the recorded final verdict and the final-layer lens score at 0.5 disagree on > 5% of items "
                 "(seen only for Qwen models; a likely but unverified cause is the lens applying the final norm to a last hidden state "
                 "that is already normed, so for these cells the 'final-layer score' used for (a'), (b) and AUROC is a close but not "
                 "identical proxy for the model's own output logits, which were not saved). "
                 "Per-cell agreement is in results.json (`final_pred_vs_lens_agree`). (a') = final-layer lens score thresholded at 0.5.\n")

    lines.append(f"## Main cells ({n_main})\n")
    lines.append(table(main_rows) + "\n")
    lines.append("## Supplementary: RB2-Safety and JudgeBench runs on disk (not part of the 42)\n")
    lines.append("These have per-item per-layer scores locally but are outside the 42-cell grid (only gpt-oss-120b has a saved "
                 "significance file for them). Same protocol.\n")
    cs = counts(sup_rows)
    lines.append("Counts: " + ", ".join(f"{k}: {len(v)}" for k, v in sorted(cs.items())) + "\n")
    lines.append(table(sup_rows) + "\n")
    lines.append("## Skipped cells (no continuous per-layer score on disk)\n")
    if skipped:
        for s in skipped:
            lines.append(f"- `{s['cell']}` ({s['group']}): {s['reason']}. Its saved held-out significance result used the "
                         "saturated legacy `decision_score` (ds) field as a stand-in, which is a valid 0/1 verdict but only "
                         "keeps the margin for items favouring CORRECT (it is exactly 0 for every item favouring INCORRECT), "
                         "so neither a cutoff nor an AUROC can be computed faithfully. The original held-out gain there was "
                         "0.000, so it would be 'no gain' regardless.")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Caveats\n")
    lines.append("- The 95% brackets are split-to-split spread, not a formal CI on the population effect; splits share items, so "
                 "a bootstrap-over-splits CI (used only for the gain/no-gain call, as in the original) is optimistic.")
    lines.append("- Both (b) and (c) get one 'free choice' on half A (a cutoff vs a layer out of ~25-89), so neither side is "
                 "favoured by over-fitting; the comparison is like-for-like.")
    lines.append("- 'Recovered' can exceed 100% (recalibrated final beats the interior layer) or be negative "
                 "(re-thresholding the final layer overfits A and hurts on B).")
    (HERE / "results.md").write_text("\n".join(lines) + "\n")
    print("wrote", HERE / "results.md")


if __name__ == "__main__":
    main()
