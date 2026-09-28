#!/usr/bin/env python3
"""
Test TypeSafe Jev as an LLM judge on BFF-Bench (Kensho "No Free Labels" data).

For every BFF-Bench model response with a consensus human label (kensho/VERDICTS),
ask Jev a yes/no (noul) question: "Is the assistant's final response correct?"
under two conditions:
  - noref : Jev sees only the conversation (reference-free judging)
  - ref   : Jev also sees the expert reference answer from kensho/BFFBench

Outputs (in --out, default ./jev_bff_results):
  predictions.jsonl  one row per (item, condition), cached so reruns resume
  summary.md         kappa / accuracy / selective-judging curve / cost / latency
  items.csv          flat table for further analysis

Usage:
  pip install typesafe-sdk datasets pandas scikit-learn
  export TYPESAFE_API_KEY=...        # your key from console.typesafe.ai (never commit it)
  python run_jev_bff.py --limit 40   # pilot run (~40 items x 2 conditions)
  python run_jev_bff.py              # full run
  python run_jev_bff.py --mock       # offline dry run with a fake Jev (tests the pipeline)
"""
import argparse, json, os, random, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

PRICE_PER_M_INPUT = 0.042  # USD per 1M input tokens (vendor list price, Sept 2026)

INSTR = ("Evaluate the assistant's FINAL response in this finance/accounting conversation. "
         "Answer yes only if it correctly answers the user's final question: the key facts, "
         "calculations, numbers and conclusions must be correct. Minor wording or formatting "
         "issues do not matter; a wrong number, wrong method or wrong conclusion makes it incorrect.")
INSTR_REF = INSTR + (" An expert-written reference answer is provided; use it as the ground truth "
                     "for what the correct answer is.")
CRITERIA = {"true": "The final response is substantively correct.",
            "false": "The final response contains a substantive error or reaches a wrong answer."}


# ----------------------------------------------------------------------------- data
def load_data(verdicts_path=None, bff_path=None):
    if verdicts_path:
        v = pd.read_parquet(verdicts_path) if verdicts_path.endswith(".parquet") else pd.read_json(verdicts_path, lines=True)
    else:
        from datasets import load_dataset
        v = load_dataset("kensho/VERDICTS", split="train").to_pandas()
    if bff_path:
        b = pd.read_parquet(bff_path) if bff_path.endswith(".parquet") else pd.read_json(bff_path, lines=True)
    else:
        from datasets import load_dataset
        b = load_dataset("kensho/BFFBench", split="train").to_pandas()
    return v, b


def _to_list(x):
    if x is None:
        return []
    if hasattr(x, "tolist"):
        x = x.tolist()
    return list(x)


def build_items(v, b, consensus="unanimous"):
    v = v[v["dataset"].astype(str).str.lower().str.contains("bff")].copy()
    # reference answers keyed by question uid (fallback: question_id)
    refs = {}
    for _, r in b.iterrows():
        rl = [str(x) for x in _to_list(r.get("references"))]
        for key in (r.get("uid"), r.get("question_id")):
            if key is not None:
                refs[str(key)] = rl
    items, dropped = [], {"no_consensus": 0, "no_ref": 0}
    for (qid, cid, turn, model), g in v.groupby(["qid", "cid", "turn", "model"]):
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
        conv = [{"role": m["role"], "content": m["content"]} for m in _to_list(g.iloc[0]["conv"])]
        rl = refs.get(str(qid), [])
        ref = rl[int(turn) - 1] if 0 < int(turn) <= len(rl) else None
        if ref is None:
            dropped["no_ref"] += 1
        items.append(dict(id=f"{cid}-t{turn}", qid=str(qid), cid=str(cid), turn=int(turn), examinee=str(model),
                          human=1 if lab == "Correct" else 0, n_annot=len(g), conv=conv, ref=ref))
    return items, dropped


# ----------------------------------------------------------------------------- judge
class JevJudge:
    def __init__(self, model="jev-latest"):
        from typesafe_sdk import TypeSafeClient, RetryPolicy
        self.client = TypeSafeClient(model=model, retry=RetryPolicy(max_retries=4, backoff_initial=0.5, backoff_max=8.0, timeout=60.0))
        self.Noul = __import__("typesafe_sdk").Noul

    def __call__(self, item, cond):
        state = {"conversation": item["conv"]}
        if cond == "ref":
            state["reference_answer_for_final_question"] = item["ref"]
        q = {"is_correct": self.Noul(instructions=INSTR_REF if cond == "ref" else INSTR, criteria=CRITERIA)}
        t0 = time.time()
        res = self.client.system_one(state=state, questions=q)
        return dict(p=float(res.nouls["is_correct"].noul), latency=time.time() - t0,
                    in_tok=res.usage.input_tokens, jev_model=res.model)


class MockJudge:
    """Fake Jev for offline testing: noisy probability correlated with the human label."""
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def __call__(self, item, cond):
        skill = 0.75 if cond == "ref" else 0.35
        base = item["human"] * skill + (1 - skill) * self.rng.random()
        p = min(max(base + self.rng.gauss(0, 0.15), 0.0), 1.0)
        return dict(p=p, latency=self.rng.uniform(0.07, 0.4), in_tok=len(json.dumps(item["conv"])) // 4, jev_model="mock")


# ----------------------------------------------------------------------------- metrics
def kappa(y, yhat):
    n = len(y)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in zip(y, yhat)) / n
    p1, q1 = sum(y) / n, sum(yhat) / n
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def auroc(y, s):
    pos = [a for a, t in zip(s, y) if t == 1]
    neg = [a for a, t in zip(s, y) if t == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def block(df):
    y, p = df["human"].tolist(), df["p"].tolist()
    yh = [int(x >= 0.5) for x in p]
    tp = sum(a and b for a, b in zip(y, yh)); tn = sum((not a) and (not b) for a, b in zip(y, yh))
    fp = sum((not a) and b for a, b in zip(y, yh)); fn = sum(a and (not b) for a, b in zip(y, yh))
    return dict(n=len(y), acc=(tp + tn) / max(len(y), 1), kappa=kappa(y, yh), auroc=auroc(y, p),
                fpr=fp / max(fp + tn, 1), fnr=fn / max(fn + tp, 1), pred_correct_rate=sum(yh) / max(len(y), 1))


def selective_curve(df, targets=(1.0, 0.9, 0.8, 0.7, 0.6, 0.5)):
    d = df.assign(conf=(df["p"] - 0.5).abs() * 2).sort_values("conf", ascending=False)
    rows = []
    for cov in targets:
        k = max(int(round(cov * len(d))), 1)
        s = d.head(k)
        b = block(s)
        rows.append(dict(coverage=k / len(d), min_conf=s["conf"].min(), acc=b["acc"], kappa=b["kappa"]))
    return rows


def fmt(x, nd=3):
    return "n/a" if x != x else f"{x:.{nd}f}"


def summarize(preds, items, out, dropped):
    df = pd.DataFrame(preds)
    meta = pd.DataFrame(items).drop(columns=["conv", "ref"])
    df = df.merge(meta, on="id")
    df.to_csv(out / "items.csv", index=False)
    L = ["# Jev on BFF-Bench: results", "",
         f"Items with consensus human labels: {len(items)} (dropped for no consensus: {dropped['no_consensus']}, "
         f"missing reference: {dropped['no_ref']}). Jev model: {', '.join(sorted(df['jev_model'].unique()))}.", "",
         "Verdict = yes if Jev's probability ≥ 0.5. κ = Cohen's kappa vs consensus human label.", "",
         "## Overall", "", "| Condition | n | Accuracy | Cohen's κ | AUROC | FPR (wrong→'correct') | FNR | Says 'correct' |",
         "|---|---|---|---|---|---|---|---|"]
    for c in ["noref", "ref"]:
        s = df[df.cond == c]
        if len(s):
            b = block(s)
            L.append(f"| {c} | {b['n']} | {fmt(b['acc'])} | {fmt(b['kappa'])} | {fmt(b['auroc'])} | {fmt(b['fpr'])} | {fmt(b['fnr'])} | {fmt(b['pred_correct_rate'])} |")
    L += ["", f"Human base rate (share labelled Correct): {fmt(meta['human'].mean())}", "",
          "Reference point from No Free Labels (single + pairwise, overall κ): GPT-4o ≈ 0.69 with human reference, ≈ 0.46 without.", "",
          "## By examinee model (κ)", "", "| Examinee | n | κ noref | κ ref | acc noref | acc ref |", "|---|---|---|---|---|---|"]
    for m, g in df.groupby("examinee"):
        a, r = g[g.cond == "noref"], g[g.cond == "ref"]
        ba, br = (block(a) if len(a) else None), (block(r) if len(r) else None)
        L.append(f"| {m} | {len(g) // max(g.cond.nunique(), 1)} | {fmt(ba['kappa']) if ba else '-'} | {fmt(br['kappa']) if br else '-'} | "
                 f"{fmt(ba['acc']) if ba else '-'} | {fmt(br['acc']) if br else '-'} |")
    L += ["", "## By turn (κ)", "", "| Turn | κ noref | κ ref |", "|---|---|---|"]
    for t, g in df.groupby("turn"):
        a, r = g[g.cond == "noref"], g[g.cond == "ref"]
        L.append(f"| {t} | {fmt(block(a)['kappa']) if len(a) else '-'} | {fmt(block(r)['kappa']) if len(r) else '-'} |")
    L += ["", "## Selective judging (accept only Jev's most confident verdicts)", "",
          "confidence = |p − 0.5| × 2. This is the Trust-or-Escalate / Path C tier-0 question: how much can Jev handle alone?", ""]
    for c in ["noref", "ref"]:
        s = df[df.cond == c]
        if not len(s):
            continue
        L += [f"**{c}**", "", "| Coverage | Min confidence | Accuracy | κ |", "|---|---|---|---|"]
        for r in selective_curve(s):
            L.append(f"| {r['coverage']:.0%} | {fmt(r['min_conf'], 2)} | {fmt(r['acc'])} | {fmt(r['kappa'])} |")
        L.append("")
    lat = df["latency"].tolist()
    tok = df["in_tok"].fillna(0).sum()
    L += ["## Cost & latency", "",
          f"- Calls: {len(df)}; input tokens: {int(tok):,}; est. cost: ${tok / 1e6 * PRICE_PER_M_INPUT:.4f} (list price ${PRICE_PER_M_INPUT}/1M input, output free)",
          f"- Latency p50 {statistics.median(lat):.3f}s, p95 {sorted(lat)[int(0.95 * (len(lat) - 1))]:.3f}s (includes network)", ""]
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="jev_bff_results")
    ap.add_argument("--limit", type=int, default=None, help="random subset of items (pilot)")
    ap.add_argument("--conditions", default="noref,ref")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--consensus", choices=["unanimous", "majority"], default="unanimous")
    ap.add_argument("--verdicts-path"); ap.add_argument("--bff-path")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    v, b = load_data(a.verdicts_path, a.bff_path)
    items, dropped = build_items(v, b, a.consensus)
    if a.limit:
        random.Random(a.seed).shuffle(items)
        items = items[: a.limit]
    print(f"{len(items)} items; conditions={a.conditions}", file=sys.stderr)

    if not a.mock and not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("Set TYPESAFE_API_KEY first (export TYPESAFE_API_KEY=...), or use --mock.")
    judge = MockJudge(a.seed) if a.mock else JevJudge(a.model)

    cache_f = out / ("predictions_mock.jsonl" if a.mock else "predictions.jsonl")
    done = {}
    if cache_f.exists():
        for line in cache_f.read_text().splitlines():
            r = json.loads(line); done[(r["id"], r["cond"])] = r
    todo = [(it, c) for it in items for c in a.conditions.split(",")
            if (it["id"], c) not in done and not (c == "ref" and it["ref"] is None)]
    print(f"{len(done)} cached, {len(todo)} to run", file=sys.stderr)

    errors = 0
    with open(cache_f, "a") as fh, ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(judge, it, c): (it, c) for it, c in todo}
        for i, f in enumerate(as_completed(futs), 1):
            it, c = futs[f]
            try:
                r = dict(id=it["id"], cond=c, **f.result())
                done[(it["id"], c)] = r
                fh.write(json.dumps(r) + "\n"); fh.flush()
            except Exception as e:  # keep going; failed items are retried on the next run
                errors += 1
                print(f"[error] {it['id']} {c}: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr)
    ids = {it["id"] for it in items}
    preds = [r for (i, _), r in done.items() if i in ids]
    if errors:
        print(f"{errors} calls failed; rerun the same command to retry them.", file=sys.stderr)
    summarize(preds, items, out, dropped)


if __name__ == "__main__":
    main()
