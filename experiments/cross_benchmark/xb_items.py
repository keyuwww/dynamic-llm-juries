"""
One item table per benchmark, in a shared shape, for annotation, the decisions table and the analyses.

Columns: bench, key (matches judgments: see judgment_key), group (CV / bootstrap unit), pair_id, fmt
(single | pair), order, category, gold (1 = good / first-shown better; None = no majority), votes (list of
human votes as strings, or None), examinee, question_key, question (text an annotator codes), resp_len
(characters of the judged response; pair: first-shown minus second-shown), len_a, len_b.

Benches: bff, mtb (VERDICTS halves), bffpair (VERDICTSPairwise), safety (RewardBench 2 Safety), bbeh (BBEH Mini,
pool answers), judgebench, rb2, alpacafarm, mtbhuman, dpo5k (loaders.py).
"""
import ast
import collections
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tinker_pool"))
sys.path.insert(0, str(HERE.parent / "jev_bff"))

BENCHES = ["bff", "mtb", "bffpair", "safety", "bbeh", "judgebench", "rb2", "alpacafarm", "mtbhuman", "dpo5k"]
TITLE = {"bff": "BFF-Bench", "mtb": "(C)MT-Bench", "bffpair": "BFF-Bench pairwise", "safety": "RewardBench 2 Safety",
         "bbeh": "BBEH Mini", "judgebench": "JudgeBench", "rb2": "RewardBench 2 (other)", "alpacafarm": "AlpacaFarm human",
         "mtbhuman": "MT-Bench human", "dpo5k": "llm-judge-dpo-5k", "triviaqa": "TriviaQA judge set"}


def judgment_key(r):
    """Key of a judgment row in the item table."""
    if r.get("bench") in (None, "bff", "mtb") and "examinee" in r and r["item_id"].count("|") == 0 and "-t" in r["item_id"]:
        return f"{r['item_id']}|{r['examinee']}"
    return r["item_id"]


def _final(x):
    if isinstance(x, list):
        return x[-1]["content"] if x else ""
    return x


def _conv_text(conv, upto_last_user=True):
    users = [m["content"] for m in conv if m["role"] == "user"]
    return "\n\n[NEXT USER TURN]\n".join(users)


def verdicts_items(dataset):
    """Every VERDICTS response for bff or mtb, with all three votes (gold under the 2-of-3 rule; None when the
    majority is Not sure or there is none)."""
    from run_jev_bff import load_data
    v, b = load_data(None, None, dataset)
    v = v[v["dataset"].astype(str).str.lower() == ("bffbench" if dataset == "bff" else "mtbmr")]
    cats = {}
    to_uid = {}
    for r in b.itertuples():
        to_uid[str(r.uid)] = str(r.uid)
        if getattr(r, "question_id", None) not in (None, "None"):
            to_uid[str(r.question_id)] = str(r.uid)
    if dataset == "bff":
        q = pd.read_parquet(HERE.parent / "bff_annotation/final/tables/questions_annotated.parquet")
        cats = dict(zip(q.uid, q.primary_domain))
    else:
        for r in b.itertuples():
            cats[str(r.uid)] = r.category
            cats[str(r.question_id)] = r.category
    rows = []
    for (qid, cid, turn, model), g in v.groupby(["qid", "cid", "turn", "model"]):
        votes = [str(x).lower() for x in g["label"]]
        c, i = votes.count("correct"), votes.count("incorrect")
        gold = 1 if c >= 2 else 0 if i >= 2 else None
        conv = list(g.iloc[0]["conv"])
        conv = [dict(role=m["role"], content=m["content"]) for m in conv]
        resp = conv[-1]["content"] if conv and conv[-1]["role"] == "assistant" else ""
        rows.append(dict(bench=dataset, key=f"{cid}-t{int(turn)}|{model}", group=to_uid.get(str(qid), str(qid)), pair_id=None, fmt="single",
                         order=0, category=cats.get(str(qid), cats.get(str(cid), "unknown")), gold=gold, votes=votes,
                         examinee=str(model), question_key=f"{to_uid.get(str(qid), str(qid))}-t{int(turn)}",
                         question=_conv_text(conv[:-1]), resp_len=len(resp), len_a=len(resp), len_b=None,
                         response=resp))
    return pd.DataFrame(rows)


def bffpair_items():
    from data import load_pairwise_items
    q = pd.read_parquet(HERE.parent / "bff_annotation/final/tables/questions_annotated.parquet")
    dom = dict(zip(q.uid, q.primary_domain))
    rows = []
    for it in load_pairwise_items():
        la, lb = len(it["conv_a"][-1]["content"]), len(it["conv_b"][-1]["content"])
        rows.append(dict(bench="bffpair", key=it["id"], group=it["uid"], pair_id=it["pair_id"], fmt="pair",
                         order=0 if it["order"] == "ab" else 1, category=dom.get(it["uid"], "unknown"), gold=it["gold"],
                         votes=None, examinee=it["examinee"], question_key=f"{it['uid']}-t{it['turn']}",
                         question=_conv_text(it["conv_a"][:-1]), resp_len=la - lb, len_a=la, len_b=lb,
                         resp_a=it["conv_a"][-1]["content"], resp_b=it["conv_b"][-1]["content"]))
    return pd.DataFrame(rows)


def safety_items():
    from datasets import load_dataset
    d = load_dataset("allenai/reward-bench-2", split="test")
    rows = []
    for r in d:
        if r["subset"] != "Safety":
            continue
        meta = r["additional_metadata"] if isinstance(r["additional_metadata"], dict) else ast.literal_eval(str(r["additional_metadata"]))
        models = r["models"] if isinstance(r["models"], list) else ast.literal_eval(str(r["models"]))
        resps = [("chosen", i, x, 1) for i, x in enumerate(r["chosen"])] + [("rejected", i, x, 0) for i, x in enumerate(r["rejected"])]
        for n, (kind, i, x, g) in enumerate(resps):
            rows.append(dict(bench="safety", key=f"rb2safety-{r['id']}-{kind}{i}", group=f"s{r['id']}", pair_id=None,
                             fmt="single", order=0, category=meta.get("category") or "unknown", gold=g, votes=None,
                             examinee=str(models[n]) if n < len(models) else "unknown", question_key=f"s{r['id']}",
                             question=str(r["prompt"]), resp_len=len(str(x)), len_a=len(str(x)), len_b=None,
                             subcategory=meta.get("subcategory"), response=str(x)))
    return pd.DataFrame(rows)


def bbeh_items(answers_path):
    """Pool answers to BBEH Mini (auto-graded) as single-grading items, all 8 answers per question."""
    rows = []
    task_name = {}
    for line in open(answers_path):
        r = json.loads(line)
        q = r["messages"][0]["content"]
        task_name.setdefault(r["task"], " ".join(q.split()[:6]))
        rows.append(dict(bench="bbeh", key=f"{r['item']}|{r['model']}", group=r["item"], pair_id=None, fmt="single",
                         order=0, category=r["task"], gold=r.get("correct"), votes=None, examinee=r["model"],
                         question_key=r["item"], question=q, resp_len=len(r.get("answer") or ""),
                         len_a=len(r.get("answer") or ""), len_b=None, response=r.get("answer") or ""))
    d = pd.DataFrame(rows)
    d["task_hint"] = d.category.map(task_name)
    return d


MTB_CATEGORY = ["writing", "roleplay", "reasoning", "math", "coding", "extraction", "stem", "humanities"]


def loader_items(bench, include_skipped=True):
    from loaders import LOADERS
    rows = []
    for it in LOADERS[bench]():
        if it.get("skip") and not include_skipped:
            continue
        if it["fmt"] == "pair":
            if bench == "mtbhuman" and not it.get("skip"):
                la, lb = len(it["resp_a"][-1]["content"]), len(it["resp_b"][-1]["content"])
            elif it.get("skip"):
                la = lb = None
            else:
                la, lb = len(it["resp_a"]), len(it["resp_b"])
            q = it.get("question") or (_conv_text(it["resp_a"][:-1]) if not it.get("skip") else "")
            cat = MTB_CATEGORY[(int(it["category"]) - 81) // 10] if bench == "mtbhuman" else it["category"]
            rows.append(dict(bench=bench, key=it["id"], group=it["group"], pair_id=it["pair_id"], fmt="pair",
                             order=it["order"], category=cat, gold=it["gold"], votes=it.get("votes"),
                             examinee=it.get("examinee", "unknown"), question_key=it["pair_id"] if bench != "mtbhuman" else f"{it.get('qid')}-t{it.get('turn')}",
                             question=q, resp_len=(la - lb) if la is not None else None, len_a=la, len_b=lb,
                             skip=bool(it.get("skip")), resp_a=_final(it.get("resp_a")), resp_b=_final(it.get("resp_b"))))
        else:
            rows.append(dict(bench=bench, key=it["id"], group=it["group"], pair_id=None, fmt="single", order=0,
                             category=it["category"], gold=it["gold"], votes=None, examinee=it.get("examinee", "unknown"),
                             question_key=it["group"], question=it["prompt"], resp_len=len(it["response"]),
                             len_a=len(it["response"]), len_b=None, skip=False, response=it["response"]))
    return pd.DataFrame(rows)


def build(bench, work):
    """work = folder holding tinker_pool/ (for BBEH answers)."""
    if bench in ("bff", "mtb"):
        return verdicts_items(bench)
    if bench == "bffpair":
        return bffpair_items()
    if bench == "safety":
        return safety_items()
    if bench == "bbeh":
        return bbeh_items(Path(work) / "tinker_pool/bbeh_results/answers.jsonl")
    return loader_items(bench)
