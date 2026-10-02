#!/usr/bin/env python3
"""
Jev as a cost-aware ROUTER over the Tinker pool, from the question alone (step 1 of the information ladder).

One Jev call per question asks everything at once (Jev never sees any model's answer):
  answerer     Choice: "Choose the model capable of answering this question correctly. Don't overshoot..."
  judge_cheap  Choice: "Choose a capable judge for this question that is also cheap. Don't overshoot."
  judge_human  Choice: "Which judge is capable enough and will align with human/expert judgment? Don't
               overshoot, save cost."
  p_answer_<m> Noul per model: will this model answer correctly?   -> threshold rule below
  p_judge_<m>  Noul per model: will this model judge answers to this question correctly?

The per-model probabilities are turned into a pick with an explicit, tunable cost rule:
  "cheapest model with P >= tau, else the highest-P model", swept over tau -> a cost/accuracy curve,
which makes the overshoot trade-off visible instead of hiding it inside one Choice.

Every model's size and Tinker price is shown to Jev. Scored against:
  answer target  Phase 1 labels (bff: Jev+ref proxy grades, turn 1 only; bbeh: auto-grader)
  judge target   Phase 2 labels (share of that question's candidates the judge got right, condition none)

Metrics per strategy: accuracy of the pick, $ per call of the picked model (measured), overshoot rate
(pick was right but a strictly cheaper model was also right), miss rate (pick wrong, some model right).
Baselines: random, always-best-single, always-cheapest, oracle, cheapest-correct oracle.

  uv run python experiments/tinker_pool/run_router.py --bench bff --mock
  uv run python experiments/tinker_pool/run_router.py --bench bff
  uv run python experiments/tinker_pool/run_router.py --bench bbeh --limit 100
"""
import argparse, json, random, statistics, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
from common import JsonlCache, POOL_BY_KEY, auroc, fmt, load_env, select_models  # noqa: E402
from data import load_bbeh_mini, load_bff  # noqa: E402

JEV_PRICE_PER_M_INPUT = 0.042
TAUS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

PROMPTS = {
    "answerer": ("Choose the model that is capable of answering this question correctly. Don't overshoot: "
                 "among models you expect to be capable, prefer the cheaper one."),
    "judge_cheap": ("Choose the judge model that is capable of correctly judging whether an answer to this "
                    "question is right, and that is also cheap. Don't overshoot: pick the cheapest judge you "
                    "expect to be capable."),
    "judge_human": ("Which judge model is capable enough to judge answers to this question and will agree with "
                    "human expert judgments? Don't overshoot and save cost: prefer a cheaper judge when it is "
                    "capable enough."),
}
P_ANSWER = ("You are predicting, BEFORE it answers, whether this AI model would answer the question below "
            "correctly (right facts, calculations and conclusions). Base it on the model's size and family and "
            "on how hard this question is. Model: {blurb}")
P_JUDGE = ("You are predicting whether this AI model, acting as a judge, would correctly decide whether a given "
           "answer to the question below is right or wrong (agreeing with a human expert). Base it on the "
           "model's size and family and on how hard the question is to verify. Model: {blurb}")
CRIT_ANS = {"true": "This model would likely answer correctly.", "false": "This model would likely make a substantive error."}
CRIT_JUDGE = {"true": "This model would likely judge answers to this question correctly.",
              "false": "This model would likely misjudge answers to this question."}


def blurb(m):
    s = POOL_BY_KEY[m]
    return (f"{s['model']} ({s['family']} family; {s['params']} total parameters, {s['active']} active per token; "
            f"Tinker price ${s['price_in']}/1M input, ${s['price_out']}/1M output tokens)")


def questions(bench, a):
    """[(qid used for labels, question text)]"""
    if bench == "bff":
        return [(f"{r['uid']}|1", r["turns"][0]) for r in load_bff(a.bff_path)]
    return [(f"{e['id']}|1", e["input"]) for e in load_bbeh_mini(a.bbeh_path)]


def labels(bench, sfx):
    """answer[qid][model] = 0/1 ; judge[qid][model] = share of candidates judged right ; cost[target][model] = $/call"""
    out = HERE / (f"mock_{bench}_results" if sfx else f"{bench}_results")
    ans, jud = defaultdict(dict), defaultdict(lambda: defaultdict(list))
    cost = {"answer": defaultdict(list), "judge": defaultdict(list)}
    a_rows = JsonlCache(out / f"answers{sfx}.jsonl").rows.values()
    for r in a_rows:
        cost["answer"][r["model"]].append(POOL_BY_KEY[r["model"]]["price_in"] * (r["n_in"] or 0) / 1e6 +
                                          POOL_BY_KEY[r["model"]]["price_out"] * (r["n_out"] or 0) / 1e6)
        if bench == "bbeh":
            ans[f"{r['item']}|{r['turn']}"][r["model"]] = r["correct"]
    if bench == "bff":
        for r in JsonlCache(out / f"grades{sfx}.jsonl").rows.values():
            if r["grader"] == "jev":
                ans[f"{r['item']}|{r['turn']}"][r["model"]] = r["correct"]
    jpath = out / f"judgments{sfx}.jsonl"
    if jpath.exists():
        for r in JsonlCache(jpath).rows.values():
            if r["condition"] != "none" or r["vote_share"] is None:
                continue
            if bench == "bff":  # item_id = "<cid>-t<turn>"; keep turn-1 judgments, map conversation -> question uid
                if not r["item_id"].endswith("-t1"):
                    continue
                qid = None  # filled below from the judge item table
            else:
                qid = r["item_id"].split("|")[0] + "|1"
            right = int((1 if r["vote_share"] > 0.5 else 0) == r["gold"])
            cost["judge"][r["judge"]].append(r.get("cost") or 0)
            if qid:
                jud[qid][r["judge"]].append(right)
            else:
                jud[("bff-cid", r["item_id"])][r["judge"]].append(right)
    return ans, jud, {t: {m: statistics.mean(v) for m, v in d.items()} for t, d in cost.items()}


def attach_bff_judge_qids(jud, a):
    """VERDICTS judge items are keyed by conversation id; map them to the BFF question uid."""
    keyed = [k for k in jud if isinstance(k, tuple)]
    if not keyed:
        return jud
    from data import load_verdicts_items, bff_key_to_uid
    items, _ = load_verdicts_items(a.verdicts_path, a.bff_path)
    to_uid = bff_key_to_uid(load_bff(a.bff_path))
    cid2q = {it["id"]: f"{to_uid.get(it['qid'], it['qid'])}|1" for it in items}
    for k in keyed:
        q = cid2q.get(k[1])
        if q:
            for m, v in jud[k].items():
                jud[q][m].extend(v)
        del jud[k]
    return jud


# ----------------------------------------------------------------------------- Jev calls
def ask_jev(models, mock, jev_model):
    if mock:
        rng = random.Random(0)

        def call(qtext):
            p = {m: rng.random() for m in models}
            ch = lambda: {m: v / sum(p.values()) for m, v in p.items()}  # noqa: E731
            return dict(p_answer=p, p_judge={m: rng.random() for m in models},
                        choice={k: ch() for k in PROMPTS}, in_tok=len(qtext) // 4)
        return call
    load_env()
    from backends import Backend, get_noul, get_choice_probs
    b = Backend("jev", jev_model)

    def call(qtext):
        state = {"question": qtext, "candidate_models": {m: blurb(m) for m in models}}
        q = {k: b.Choice(instructions=v, criteria={m: blurb(m) for m in models}) for k, v in PROMPTS.items()}
        for m in models:
            q[f"p_answer_{m}"] = b.Noul(instructions=P_ANSWER.format(blurb=blurb(m)), criteria=CRIT_ANS)
            q[f"p_judge_{m}"] = b.Noul(instructions=P_JUDGE.format(blurb=blurb(m)), criteria=CRIT_JUDGE)
        res, meta = b.ask(state, q)
        return dict(p_answer={m: get_noul(res, f"p_answer_{m}") for m in models},
                    p_judge={m: get_noul(res, f"p_judge_{m}") for m in models},
                    choice={k: get_choice_probs(res, k) for k in PROMPTS}, in_tok=meta["in_tok"])
    return call


# ----------------------------------------------------------------------------- scoring
def score(picks, lab, price, models):
    """picks: {qid: model}. lab: {qid: {model: value in [0,1]}}."""
    qs = [q for q in picks if q in lab and all(m in lab[q] for m in models)]
    if not qs:
        return None
    acc = statistics.mean(lab[q][picks[q]] for q in qs)
    cost = statistics.mean(price.get(picks[q], 0) for q in qs)
    over = statistics.mean(1 if lab[q][picks[q]] >= 0.5 and any(
        lab[q][m] >= 0.5 and price.get(m, 0) < price.get(picks[q], 0) for m in models) else 0 for q in qs)
    miss = statistics.mean(1 if lab[q][picks[q]] < 0.5 and max(lab[q][m] for m in models) >= 0.5 else 0 for q in qs)
    return dict(n=len(qs), acc=acc, cost=cost, over=over, miss=miss)


def baselines(lab, price, models, qs):
    qs = [q for q in qs if q in lab and all(m in lab[q] for m in models)]
    if not qs:
        return {}
    mean = {m: statistics.mean(lab[q][m] for q in qs) for m in models}
    best = max(mean, key=mean.get)
    cheapest = min(models, key=lambda m: price.get(m, 0))
    rng = random.Random(0)
    out = {"random": {q: rng.choice(models) for q in qs},
           f"always best single ({best})": {q: best for q in qs},
           f"always cheapest ({cheapest})": {q: cheapest for q in qs},
           "oracle (best model per question)": {q: max(models, key=lambda m: (lab[q][m], -price.get(m, 0))) for q in qs}}
    return out


def table(name, strategies, lab, price, models):
    L = [f"## {name}", "", "| Strategy | n | Accuracy | $ / call (picked model) | Overshoot | Miss |", "|---|---|---|---|---|---|"]
    for sname, picks in strategies:
        s = score(picks, lab, price, models)
        if s:
            L.append(f"| {sname} | {s['n']} | {fmt(s['acc'])} | ${s['cost']:.5f} | {fmt(s['over'])} | {fmt(s['miss'])} |")
    return L + [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", choices=["bff", "bbeh"], required=True)
    ap.add_argument("--models", default="routing", help="candidates Jev chooses among (default: routing pool)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--jev-model", default="jev-1.13.0")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--bff-path"), ap.add_argument("--verdicts-path"), ap.add_argument("--bbeh-path")
    a = ap.parse_args()
    models = [m["key"] for m in select_models(a.models)]
    sfx = "_mock" if a.mock else ""
    out = HERE / (f"mock_{a.bench}_results" if a.mock else f"{a.bench}_results")
    out.mkdir(exist_ok=True)

    qs = questions(a.bench, a)
    if a.limit:
        qs = qs[: a.limit]
    cache = JsonlCache(out / f"router{sfx}.jsonl")
    tag = ",".join(models)
    todo = [(q, t) for q, t in qs if f"{tag}|{q}" not in cache]
    call = ask_jev(models, a.mock, a.jev_model)
    print(f"{len(qs)} questions, {len(todo)} Jev calls to make", flush=True)
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(call, t): q for q, t in todo}
        for i, f in enumerate(as_completed(futs), 1):
            q = futs[f]
            try:
                cache.put(dict(cache_key=f"{tag}|{q}", qid=q, models=models, **f.result()))
            except Exception as e:  # noqa: BLE001
                print(f"[error] {q}: {type(e).__name__}: {str(e)[:200]}")
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    preds = {r["qid"]: r for r in cache.rows.values() if r["models"] == models}

    ans, jud, cost = labels(a.bench, sfx)
    if a.bench == "bff":
        jud = attach_bff_judge_qids(jud, a)
    jud = {q: {m: statistics.mean(v) for m, v in d.items()} for q, d in jud.items()}

    L = [f"# Jev router over the Tinker pool: {a.bench}", "",
         f"Candidates: {', '.join(models)}. Jev sees only the question plus each model's size and price.", ""]
    for target, lab, pkey, choice_keys in [("answer", ans, "p_answer", ["answerer"]),
                                            ("judge", jud, "p_judge", ["judge_cheap", "judge_human"])]:
        price = cost[target] or {m: POOL_BY_KEY[m]["price_out"] / 1e3 for m in models}
        if not lab:
            L += [f"## Target: {target}", "", f"(no {target} labels yet: run Phase {'1' if target == 'answer' else '2'} first)", ""]
            continue
        strategies = list(baselines(lab, price, models, preds).items())
        for ck in PROMPTS:  # score every prompt on both targets: shows whether the wording matters
            strategies.append((f"Jev Choice: {ck}" + (" ◀ intended target" if ck in choice_keys else ""),
                               {q: max(r["choice"][ck], key=r["choice"][ck].get) for q, r in preds.items()}))
        for tau in TAUS:
            strategies.append((f"Jev P({target}) ≥ {tau}: cheapest qualifying, else top-P",
                               {q: (min([m for m in models if r[pkey][m] >= tau], key=lambda m: price.get(m, 0))
                                    if any(r[pkey][m] >= tau for m in models) else max(models, key=lambda m: r[pkey][m]))
                                for q, r in preds.items()}))
        L += table(f"Target: {target} ({'Phase 1 answer correctness' if target == 'answer' else 'Phase 2 judge accuracy, condition none'})",
                   strategies, lab, price, models)
        ys, ss = [], []
        for q, r in preds.items():
            for m in models:
                if q in lab and m in lab[q]:
                    ys.append(1 if lab[q][m] >= 0.5 else 0)
                    ss.append(r[pkey][m])
        L += [f"Calibration of Jev's P({target}) per (question, model): AUROC {fmt(auroc(ys, ss))} (n={len(ys)})", ""]
    tok = sum(r.get("in_tok") or 0 for r in preds.values())
    L += [f"Jev routing cost: ~${tok / 1e6 * JEV_PRICE_PER_M_INPUT:.3f} for {len(preds)} calls.", "",
          "Overshoot = picked model was right but a strictly cheaper candidate was also right. "
          "Miss = picked model was wrong although some candidate was right.", ""]
    (out / "router_summary.md").write_text("\n".join(L))
    (out / "router_metrics.json").write_text(json.dumps(dict(models=models, n=len(preds)), indent=2))
    print("\n".join(L))


if __name__ == "__main__":
    main()
