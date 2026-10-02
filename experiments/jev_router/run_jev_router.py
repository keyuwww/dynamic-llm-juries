#!/usr/bin/env python3
"""
Test whether a "System One" model (Jev or CLM-8B, see experiments/common/backends.py)
can act as a ROUTER: given only a finance/accounting question (no model response),
predict which of six candidate LLMs is most likely to answer it correctly (Path A:
"certifier router" from the project README).

Uses turn-1 items only from kensho/VERDICTS + kensho/BFFBench. At turn 1, all six
examinee models answer the identical first user question, so it's the one place in
the data where "which model should we route this to" is an apples-to-apples
comparison. (At turn 2 the preceding turn already differs per model, since each
model wrote its own turn-1 answer.)

For every question, one system_one call asks the backend three kinds of things,
never shown any model's actual response:
  - would_<model>_be_correct (Noul, one per candidate): independent yes/no per model
  - best_model (Choice, one call): pick among the candidates directly
  - none_correct (Noul): will *none* of the candidates get this right?

Per question this is compared against:
  - random pick (expected accuracy = mean correct-rate across the candidates)
  - always picking the single globally-best-performing model (fixed baseline)
  - the backend's noul-argmax pick, and its choice pick
  - oracle (correct whenever at least one candidate got it right)

Outputs (in --out, default experiments/jev_router/<backend>_router_results):
  predictions.jsonl         one row per question, cached so reruns resume
  summary.md                routing accuracy vs baselines + calibration
  items.csv                 flat per-(question, model) table
  routing_by_question.csv   flat per-question table
  metrics.json              machine-readable summary for experiments/compare_backends.py

Usage:
  uv sync
  export TYPESAFE_API_KEY=...                    # from console.typesafe.ai
  uv run python run_jev_router.py --limit 20      # pilot (~20 questions)
  uv run python run_jev_router.py                 # full run
  uv run python run_jev_router.py --backend clm --clm-url http://127.0.0.1:8700
  uv run python run_jev_router.py --mock          # offline dry run with a fake backend
"""
import argparse, json, os, random, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

PRICE_PER_M_INPUT = 0.042  # USD per 1M input tokens (vendor list price, Sept 2026)

MODEL_BLURB = {
    "gemma-2-2b": "Gemma 2 2B, a small open-weight model (2 billion parameters).",
    "gpt-4o": "GPT-4o, a large frontier proprietary model from OpenAI.",
    "llama-3.3-70b": "Llama 3.3 70B, a large open-weight model (70 billion parameters).",
    "phi-4": "Phi-4, a mid-sized open-weight model optimized for reasoning.",
    "qwen2.5-7b": "Qwen2.5 7B, a small-to-mid open-weight model (7 billion parameters).",
    "yi1.5-34b-16k": "Yi-1.5 34B (16k context), a mid-to-large open-weight model.",
}

NOUL_INSTR = ("You are predicting, BEFORE it answers, whether a specific AI assistant model would "
              "correctly answer the user's finance/accounting question below. Base your estimate on "
              "the model's general skill level (described below) and on how hard this particular "
              "question is -- not on any actual response, since none has been generated yet. Answer "
              "yes if you believe this model would answer correctly (right facts, calculations and "
              "conclusions); no if you believe it would make a substantive error. Model: {model} -- {blurb}")
NOUL_CRITERIA = {"true": "This model would likely answer the question correctly.",
                  "false": "This model would likely make a substantive error."}
CHOICE_INSTR = ("Given the finance/accounting question below, which of these candidate AI assistant "
                "models is most likely to answer it correctly? Judge from each model's general skill "
                "level and how hard this particular question is.")
NONE_INSTR = ("Given the finance/accounting question below and this same set of candidate models, is "
              "it likely that NONE of them would answer it correctly (i.e. this question is hard "
              "enough that every one of these models would make a substantive error)?")
NONE_CRITERIA = {"true": "None of the candidate models would likely get this right.",
                  "false": "At least one candidate model would likely get this right."}


# ----------------------------------------------------------------------------- data
def load_data(verdicts_path=None):
    if verdicts_path:
        v = pd.read_parquet(verdicts_path) if verdicts_path.endswith(".parquet") else pd.read_json(verdicts_path, lines=True)
    else:
        from datasets import load_dataset
        v = load_dataset("kensho/VERDICTS", split="train").to_pandas()
    return v


def build_items(v, consensus="unanimous", turn=1):
    """turn=1: the shared prompt (all 6 models see the identical first question) is exactly what
    was actually shown to every model -- a fair routing comparison.
    turn=2: EACH model's real turn-2 input included its OWN turn-1 answer, which differs per model
    -- there is no shared prompt at turn 2 in reality. We approximate one anyway (per user request)
    by using only the turn-2 question text alone, dropping the turn-1 context entirely. This makes
    the routing call comparable across candidates, but it means Jev is judging with LESS context
    than the real responses were actually generated with -- a real deployed router would not have
    this option. Treat turn=2 results as an exploratory approximation, not a like-for-like result
    with turn=1."""
    v = v[v["dataset"].astype(str).str.lower().str.contains("bff")].copy()
    v = v[v["turn"] == turn]
    q_idx = 2 * (turn - 1)  # conv = [user1, asst1, user2, asst2, ...]; turn t's question is at 2*(t-1)
    per_model, dropped = {}, {"no_consensus": 0}
    for (qid, model), g in v.groupby(["qid", "model"]):
        labs = [l for l in g["label"].astype(str) if l.lower() in ("correct", "incorrect")]
        if consensus == "unanimous":
            ok = len(labs) >= 1 and len(set(labs)) == 1 and (g["label"].astype(str).str.lower() != "not sure").all()
            lab = labs[0] if ok else None
        else:  # majority
            lab = None
            if labs:
                c, i = labs.count("Correct"), labs.count("Incorrect")
                lab = "Correct" if c > i else "Incorrect" if i > c else None
        if lab is None:
            dropped["no_consensus"] += 1
            continue
        conv = g.iloc[0]["conv"]
        question = str(conv[q_idx]["content"])  # this turn's user question alone (see docstring)
        per_model.setdefault(str(qid), dict(qid=str(qid), question=question, candidates={}))
        per_model[str(qid)]["candidates"][str(model)] = 1 if lab == "Correct" else 0
    # one item per QUESTION now (holds all its candidate models' labels)
    items = [v for v in per_model.values() if len(v["candidates"]) >= 2]
    return items, dropped


# ----------------------------------------------------------------------------- router
class SystemOneRouter:
    def __init__(self, backend="jev", model=None, clm_url=None):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
        from backends import Backend, get_noul, get_choice_probs
        self.b = Backend(backend, model, clm_url)
        self.get_noul, self.get_choice_probs = get_noul, get_choice_probs

    def __call__(self, item):
        candidates = sorted(item["candidates"])
        state = {"question": item["question"],
                  "candidates": {m: MODEL_BLURB.get(m, m) for m in candidates}}
        q = {f"would_{m}_be_correct": self.b.Noul(
                instructions=NOUL_INSTR.format(model=m, blurb=MODEL_BLURB.get(m, m)), criteria=NOUL_CRITERIA)
             for m in candidates}
        q["best_model"] = self.b.Choice(instructions=CHOICE_INSTR,
                                        criteria={m: MODEL_BLURB.get(m, m) for m in candidates})
        q["none_correct"] = self.b.Noul(instructions=NONE_INSTR, criteria=NONE_CRITERIA)
        t0 = time.time()
        res, meta = self.b.ask(state, q)
        noul_p = {m: self.get_noul(res, f"would_{m}_be_correct") for m in candidates}
        choice_p = self.get_choice_probs(res, "best_model")
        none_p = self.get_noul(res, "none_correct")
        return dict(noul_p=noul_p, choice_p=choice_p, none_p=none_p, latency=time.time() - t0,
                    in_tok=meta["in_tok"], backend_model=meta["backend_model"])


class Sampled:
    """Wrap a router callable to repeat each question's call N times and average the
    probabilities (denoising), keeping the raw per-sample values too so the spread can
    be inspected. N=1 is a plain passthrough."""
    def __init__(self, inner, n=1):
        self.inner, self.n = inner, n

    def __call__(self, item):
        if self.n <= 1:
            r = self.inner(item)
            r["noul_p_samples"] = {m: [p] for m, p in r["noul_p"].items()}
            return r
        runs = [self.inner(item) for _ in range(self.n)]
        candidates = sorted(item["candidates"])
        noul_p_samples = {m: [r["noul_p"][m] for r in runs] for m in candidates}
        noul_p = {m: sum(vs) / len(vs) for m, vs in noul_p_samples.items()}
        keys = set().union(*(r["choice_p"] for r in runs))
        choice_avg = {k: sum(r["choice_p"].get(k, 0.0) for r in runs) / self.n for k in keys}
        z = sum(choice_avg.values()) or 1.0
        choice_p = {k: v / z for k, v in choice_avg.items()}
        none_p = sum(r["none_p"] for r in runs) / self.n
        return dict(noul_p=noul_p, choice_p=choice_p, none_p=none_p, noul_p_samples=noul_p_samples,
                    latency=sum(r["latency"] for r in runs), in_tok=sum(r["in_tok"] or 0 for r in runs),
                    backend_model=runs[0]["backend_model"])


class MockRouter:
    """Fake backend for offline testing: noisy probabilities correlated with the human labels,
    with a per-model skill offset so bigger/named models look plausibly stronger."""
    SKILL = {"gemma-2-2b": 0.3, "qwen2.5-7b": 0.45, "phi-4": 0.55,
             "yi1.5-34b-16k": 0.55, "llama-3.3-70b": 0.65, "gpt-4o": 0.75}

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def __call__(self, item):
        candidates = sorted(item["candidates"])
        skill = 0.6  # how much the guess tracks the true label vs. just model-name prior
        noul_p = {}
        for m in candidates:
            prior = self.SKILL.get(m, 0.5)
            base = item["candidates"][m] * skill + (1 - skill) * prior
            noul_p[m] = min(max(base + self.rng.gauss(0, 0.15), 0.0), 1.0)
        raw = {m: max(noul_p[m], 1e-6) for m in candidates}
        z = sum(raw.values())
        choice_p = {m: v / z for m, v in raw.items()}
        none_p = min(max(1 - max(noul_p.values()) + self.rng.gauss(0, 0.05), 0.0), 1.0)
        return dict(noul_p=noul_p, choice_p=choice_p, none_p=none_p,
                    latency=self.rng.uniform(0.07, 0.4), in_tok=len(item["question"]) // 4, backend_model="mock")


# ----------------------------------------------------------------------------- metrics
def auroc(y, s):
    pos = [a for a, t in zip(s, y) if t == 1]
    neg = [a for a, t in zip(s, y) if t == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def brier(y, s):
    if not y:
        return float("nan")
    return sum((p - t) ** 2 for p, t in zip(s, y)) / len(y)


def fmt(x, nd=3):
    return "n/a" if x is None or x != x else f"{x:.{nd}f}"


def jury_analysis(flat, threshold, cap):
    """Per question: take candidates with averaged P(correct) > threshold, sorted desc,
    capped at `cap` members -- the dynamic jury this project is actually about. Scored by
    majority vote of the jury members' REAL correctness (ties count as incorrect, since a
    split jury shouldn't be trusted); 0-member questions are 'escalated', not scored."""
    rows = []
    for qid, g in flat.groupby("qid"):
        g = g.sort_values("noul_p", ascending=False)
        jury = g[g.noul_p > threshold].head(cap)
        size = len(jury)
        if size == 0:
            rows.append(dict(qid=qid, jury_size=0, jury_members=None, majority_correct=None, any_correct=None))
            continue
        correct = int(jury["human"].sum())
        rows.append(dict(qid=qid, jury_size=size, jury_members=",".join(jury["model"]),
                          majority_correct=int(correct > size / 2), any_correct=int(correct >= 1)))
    return pd.DataFrame(rows)


def summarize(preds, items, out, dropped, jury_threshold=0.6, jury_cap=3):
    by_qid = {it["qid"]: it for it in items}
    flat_rows, q_rows = [], []
    for qid, r in preds.items():
        it = by_qid[qid]
        candidates = sorted(it["candidates"])
        for m in candidates:
            flat_rows.append(dict(qid=qid, model=m, human=it["candidates"][m], noul_p=r["noul_p"][m],
                                  choice_p=r["choice_p"].get(m, float("nan"))))
        q_rows.append(dict(qid=qid, n_models=len(candidates), none_p=r["none_p"],
                            none_true=int(max(it["candidates"].values()) == 0),
                            latency=r["latency"], in_tok=r["in_tok"], backend_model=r["backend_model"]))
    flat = pd.DataFrame(flat_rows)
    flat.to_csv(out / "items.csv", index=False)
    qdf = pd.DataFrame(q_rows)

    # -- overall per-model correct rate (defines "always pick the fixed best model" + the prior baseline)
    per_model = flat.groupby("model")["human"].mean().sort_values(ascending=False)
    fixed_best = per_model.index[0]

    # -- per-(question, model) calibration: noul, and a naive "prior" baseline (just the model's own
    #    overall correct rate, i.e. zero question-level signal)
    y = flat["human"].tolist()
    p_noul = flat["noul_p"].tolist()
    p_prior = flat["model"].map(per_model).tolist()
    calib = dict(auroc=auroc(y, p_noul), brier=brier(y, p_noul),
                 auroc_prior=auroc(y, p_prior), brier_prior=brier(y, p_prior),
                 auroc_choice_prob=auroc(y, flat["choice_p"].fillna(0).tolist()))

    # -- per-question routing
    rows = []
    for qid, it in by_qid.items():
        if qid not in preds:
            continue
        r = preds[qid]
        candidates = sorted(it["candidates"])
        human = it["candidates"]
        noul_pick = max(candidates, key=lambda m: r["noul_p"][m])
        choice_pick = max(r["choice_p"], key=r["choice_p"].get) if r["choice_p"] else noul_pick
        fixed_hit = human.get(fixed_best)
        rows.append(dict(qid=qid, n_models=len(candidates),
                          noul_pick_model=noul_pick, noul_pick_correct=human[noul_pick],
                          choice_pick_model=choice_pick, choice_pick_correct=human.get(choice_pick, float("nan")),
                          random_expected=sum(human.values()) / len(human), oracle=max(human.values()),
                          fixed_best_hit=fixed_hit))
    r_all = pd.DataFrame(rows)
    r_all.to_csv(out / "routing_by_question.csv", index=False)

    # Compare all strategies on the SAME set of questions (those where the fixed-best model also has
    # a consensus label), so oracle/random/noul/choice/fixed are never computed on different
    # denominators -- otherwise oracle can spuriously look worse than a single fixed policy.
    r = r_all.dropna(subset=["fixed_best_hit"])
    n_dropped_for_fixed = len(r_all) - len(r)
    n_q = len(r)
    route_random = r["random_expected"].mean()
    route_best_single = r["fixed_best_hit"].mean()
    route_noul = r["noul_pick_correct"].mean()
    route_choice = r["choice_pick_correct"].mean()
    route_oracle = r["oracle"].mean()
    denom = route_oracle - route_best_single
    gap_closed_noul = (route_noul - route_best_single) / denom if denom else float("nan")
    gap_closed_choice = (route_choice - route_best_single) / denom if denom else float("nan")
    none_auroc = auroc(qdf["none_true"].tolist(), qdf["none_p"].tolist())

    # -- dynamic jury: candidates with noul_p > threshold, capped, majority-vote scored.
    # Coverage/escalation are reported over ALL questions (a property of the jury rule itself), but
    # every accuracy comparison below (jury vs. fixed-best vs. oracle) is restricted to the same `r`
    # denominator used for the routing table above (fixed-best model has a consensus label) --
    # otherwise, as with the routing table, oracle can spuriously look worse than a fixed policy.
    jr = jury_analysis(flat, jury_threshold, jury_cap)
    jr.to_csv(out / "jury_by_question.csv", index=False)
    jr_common = jr[jr.qid.isin(set(r["qid"]))]  # same denominator as the routing table (n_q questions)
    covered = jr_common[jr_common.jury_size > 0]
    jury_coverage = len(covered) / len(jr_common) if len(jr_common) else float("nan")
    jury_avg_size = covered["jury_size"].mean() if len(covered) else float("nan")
    jury_majority_acc = covered["majority_correct"].mean() if len(covered) else float("nan")
    jury_any_acc = covered["any_correct"].mean() if len(covered) else float("nan")
    # same-subset baselines, for a fair comparison against the questions the jury actually covers
    r_cov = r[r.qid.isin(set(covered["qid"]))]
    cov_best_single = r_cov["fixed_best_hit"].mean() if len(r_cov) else float("nan")
    cov_oracle = r_cov["oracle"].mean() if len(r_cov) else float("nan")

    L = ["# System One router: picking the best model per question (BFF-Bench, turn 1)", "",
         f"Questions with >=2-way consensus labels: {len(r_all)} (dropped for no consensus: {dropped['no_consensus']}). "
         f"Backend model: {', '.join(sorted(qdf['backend_model'].unique()))}.", "",
         f"Strategy comparison below uses the {n_q} of those questions where the fixed-best model "
         f"(**{fixed_best}**) also has a consensus label, so every strategy is scored on the same "
         f"denominator ({n_dropped_for_fixed} questions excluded for this table only).", "",
         "The backend never sees any model's actual response here -- only the question and a one-line "
         "description of each candidate model -- then answers three things per question: an independent "
         "yes/no per candidate, a single Choice across all candidates, and whether none would get it right.", "",
         "## Routing accuracy (share of questions where the picked model's real response was correct)", "",
         "| Strategy | Accuracy |", "|---|---|",
         f"| Random pick | {fmt(route_random)} |",
         f"| Always pick the single best-overall model (**{fixed_best}**) | {fmt(route_best_single)} |",
         f"| **Router (argmax of independent yes/no)** | **{fmt(route_noul)}** |",
         f"| **Router (single Choice call)** | **{fmt(route_choice)}** |",
         f"| Oracle (correct if *any* candidate got it right) | {fmt(route_oracle)} |", "",
         f"Gap closed vs. always-{fixed_best} (yes/no router): {fmt(gap_closed_noul)}. "
         f"Gap closed (choice router): {fmt(gap_closed_choice)}. "
         "(share of the oracle − fixed-baseline gap that the router's pick recovers; "
         "0 = no better than the fixed baseline, 1 = matches the oracle)", "",
         "## Per-model correct rate (human labels, turn 1 only)", "",
         "| Model | Correct rate |", "|---|---|"]
    for m, rate in per_model.items():
        L.append(f"| {m} | {fmt(rate)} |")
    L += ["", "## Calibration of the raw per-(question, model) prediction",
          "(treating every prediction as its own yes/no call, ignoring routing/argmax)", "",
          "| Signal | AUROC | Brier (lower better) |", "|---|---|---|",
          f"| Independent yes/no (noul) | {fmt(calib['auroc'])} | {fmt(calib['brier'])} |",
          f"| Choice probability | {fmt(calib['auroc_choice_prob'])} | n/a |",
          f"| Prior baseline (model's own overall correct rate, no question signal) | {fmt(calib['auroc_prior'])} | {fmt(calib['brier_prior'])} |",
          "", f"'None will be right' signal AUROC (predicting every candidate is wrong): {fmt(none_auroc)}", "",
          f"## Dynamic jury (P(correct) > {jury_threshold:.0%}, capped at {jury_cap})", "",
          "For each question, take the candidates with averaged P(correct) above the threshold, "
          "highest-probability first, up to the cap -- that's the jury. Scored by majority vote of "
          "the jury's REAL correctness (a split jury, e.g. 1-of-2, counts as incorrect); a question "
          "with zero qualifying candidates is escalated rather than scored.", "",
          "| | |", "|---|---|",
          f"| Coverage (share of questions with >=1 jury member) | {fmt(jury_coverage)} |",
          f"| Escalation rate (0 qualifying candidates) | {fmt(1 - jury_coverage if jury_coverage == jury_coverage else float('nan'))} |",
          f"| Average jury size, when covered | {fmt(jury_avg_size, 2)} |",
          f"| **Jury majority-vote accuracy, on covered questions** | **{fmt(jury_majority_acc)}** |",
          f"| Jury 'any member correct' rate, on covered questions | {fmt(jury_any_acc)} |",
          f"| (same-subset) always-pick-{fixed_best} accuracy | {fmt(cov_best_single)} |",
          f"| (same-subset) oracle accuracy | {fmt(cov_oracle)} |", ""]
    lat = qdf["latency"].tolist()
    tok = qdf["in_tok"].fillna(0).sum()
    n_calls = len(qdf)
    L += ["## Cost & latency", "",
          f"- Calls: {n_calls} (one combined call per question); input tokens: {int(tok):,}; "
          f"est. cost: ${tok / 1e6 * PRICE_PER_M_INPUT:.4f} (list price ${PRICE_PER_M_INPUT}/1M input, output free)",
          f"- Latency p50 {statistics.median(lat):.3f}s, p95 {sorted(lat)[int(0.95 * (len(lat) - 1))]:.3f}s (includes network)", ""]
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))

    metrics = dict(backend_model=sorted(qdf["backend_model"].unique().tolist()), n_questions=n_q,
                   auroc=calib["auroc"], auroc_choice_prob=calib["auroc_choice_prob"], auroc_prior=calib["auroc_prior"],
                   brier=calib["brier"], brier_prior=calib["brier_prior"],
                   route_random=route_random, route_best_single=route_best_single,
                   route_noul=route_noul, route_choice=route_choice, route_oracle=route_oracle,
                   gap_closed_noul=gap_closed_noul, gap_closed_choice=gap_closed_choice, none_auroc=none_auroc,
                   jury_threshold=jury_threshold, jury_cap=jury_cap, jury_coverage=jury_coverage,
                   jury_avg_size=jury_avg_size, jury_majority_acc=jury_majority_acc, jury_any_acc=jury_any_acc,
                   jury_cov_best_single=cov_best_single, jury_cov_oracle=cov_oracle)
    metrics = {k: (None if isinstance(v, float) and v != v else v) for k, v in metrics.items()}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["jev", "clm", "laya", "jeff"], default="jev", help="System One model to test")
    ap.add_argument("--clm-url", default=None, help="CLM server URL (default $CLM_URL or http://127.0.0.1:8700)")
    ap.add_argument("--out", default=None, help="default: experiments/jev_router/<backend>_router_results")
    ap.add_argument("--limit", type=int, default=None, help="random subset of questions (pilot)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--model", default=None, help="Jev model/version, e.g. jev-1.13.0 (default jev-latest)")
    ap.add_argument("--consensus", choices=["unanimous", "majority"], default="unanimous")
    ap.add_argument("--turn", type=int, choices=[1, 2], default=1,
                     help="turn=2 is an exploratory approximation -- see build_items() docstring")
    ap.add_argument("--verdicts-path")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--samples", type=int, default=1,
                     help="repeat each question's call N times and average P(correct) per candidate (denoising)")
    ap.add_argument("--jury-threshold", type=float, default=0.6,
                     help="dynamic jury: only candidates with averaged P(correct) above this qualify")
    ap.add_argument("--jury-cap", type=int, default=3, help="dynamic jury: max members, highest-probability first")
    a = ap.parse_args()

    tag = f"{a.backend}_router_results" if a.turn == 1 else f"{a.backend}_router_results_turn{a.turn}"
    out = Path(a.out or Path(__file__).resolve().parent / tag); out.mkdir(parents=True, exist_ok=True)
    v = load_data(a.verdicts_path)
    items, dropped = build_items(v, a.consensus, a.turn)
    if a.limit:
        random.Random(a.seed).shuffle(items)
        items = items[: a.limit]
    print(f"{len(items)} questions, {sum(len(it['candidates']) for it in items)} (question, model) pairs", file=sys.stderr)

    router = Sampled(MockRouter(a.seed) if a.mock else SystemOneRouter(a.backend, a.model, a.clm_url), n=a.samples)

    cache_f = out / (f"predictions_mock_s{a.samples}.jsonl" if a.mock else f"predictions_s{a.samples}.jsonl")
    done = {}
    if cache_f.exists():
        for line in cache_f.read_text().splitlines():
            r = json.loads(line); done[r["qid"]] = r
    todo = [it for it in items if it["qid"] not in done]
    print(f"{len(done)} cached, {len(todo)} to run", file=sys.stderr)

    errors = 0
    with open(cache_f, "a") as fh, ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(router, it): it for it in todo}
        for i, f in enumerate(as_completed(futs), 1):
            it = futs[f]
            try:
                r = dict(qid=it["qid"], **f.result())
                done[it["qid"]] = r
                fh.write(json.dumps(r) + "\n"); fh.flush()
            except Exception as e:
                errors += 1
                print(f"[error] {it['qid']}: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr)
    ids = {it["qid"] for it in items}
    preds = {qid: r for qid, r in done.items() if qid in ids}
    if errors:
        print(f"{errors} calls failed; rerun the same command to retry them.", file=sys.stderr)
    summarize(preds, items, out, dropped, jury_threshold=a.jury_threshold, jury_cap=a.jury_cap)


if __name__ == "__main__":
    main()
