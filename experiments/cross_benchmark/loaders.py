"""
Loaders for the benchmarks added in the cross-benchmark analysis, all returning one item shape:

  dict(id, group, bench, fmt, order, category, gold, votes, examinee, prompt-building fields...)

- fmt "single": grade one response; gold 1 = good / correct.
- fmt "pair": compare two responses; each pair appears twice (order 0 and 1, answers swapped); gold 1 = the
  first-shown response is better. A judge that always picks one position scores exactly 50%.
- group: unit for cross-validation and bootstrap (conversation / prompt / question), so both orders of a pair
  and all responses to one prompt stay together.
- votes: individual human votes when the benchmark has several per item, else None.

Benchmarks: judgebench, rb2 (RewardBench 2 Factuality / Precise IF / Math / Focus), alpacafarm (AlpacaFarm
human cross-annotations), mtbhuman (lmsys MT-Bench expert pairwise judgments), dpo5k (stindardlogic
llm-judge-dpo-5k, 15 distinct items, as a bias checklist).
"""
import ast
import collections
import json
import random


def _pair_items(bench, base_id, group, category, first, second, label_first_better, **extra):
    """Two presentations of one pair. label_first_better refers to (first, second) as given."""
    out = []
    for order, (a, b) in enumerate([(first, second), (second, first)]):
        gold = label_first_better if order == 0 else 1 - label_first_better
        out.append(dict(id=f"{base_id}|o{order}", pair_id=base_id, group=group, bench=bench, fmt="pair",
                        order=order, category=category, gold=int(gold), resp_a=a, resp_b=b, **extra))
    return out


def load_judgebench(split="gpt"):
    """ScalerLab/JudgeBench, GPT-4o response pairs (350). Labels come from verifiable ground truth."""
    from datasets import load_dataset
    d = load_dataset("ScalerLab/JudgeBench", split=split)
    items = []
    for r in d:
        if r["label"] not in ("A>B", "B>A"):
            continue
        src = r["source"]
        cat = src.split("-")[0] if src.startswith("livebench") or src.startswith("livecodebench") else src
        items += _pair_items("judgebench", r["pair_id"], r["pair_id"], cat, r["response_A"], r["response_B"],
                             int(r["label"] == "A>B"), question=r["question"], source=src,
                             examinee=r["response_model"], votes=None)
    return items


RB2_SUBSETS = ("Factuality", "Precise IF", "Math", "Focus")


def load_rb2(per_subset=60, seed=0):
    """RewardBench 2 non-Safety subsets with 1 chosen + 3 rejected completions, `per_subset` prompts each,
    flattened to single-grading items (gold 1 = chosen). Factuality and Precise IF are human / verified,
    Math is verified by answer, Focus is built by system-prompt variation (label by construction)."""
    from datasets import load_dataset
    d = load_dataset("allenai/reward-bench-2", split="test")
    rng = random.Random(seed)
    by = collections.defaultdict(list)
    for r in d:
        if r["subset"] in RB2_SUBSETS:
            by[r["subset"]].append(r)
    items = []
    for sub in RB2_SUBSETS:
        rows = by[sub]
        rng.shuffle(rows)
        for r in rows[:per_subset]:
            models = r["models"] if isinstance(r["models"], list) else ast.literal_eval(str(r["models"]))
            resps = [(x, 1) for x in r["chosen"]] + [(x, 0) for x in r["rejected"]]
            for i, (resp, g) in enumerate(resps):
                items.append(dict(id=f"rb2-{r['id']}-{i}", group=f"rb2-{r['id']}", bench="rb2", fmt="single", order=0,
                                  category=sub, gold=g, prompt=str(r["prompt"]), response=str(resp),
                                  examinee=str(models[i]) if i < len(models) else "unknown", votes=None))
    return items


def load_alpacafarm(max_pairs=None, seed=0):
    """AlpacaFarm human cross-annotations: 648 instruction/output pairs, 4 crowd votes each (preference 1 or 2).
    Gold = majority; 2-2 ties are kept with gold None so the label audit can count them, then dropped."""
    from huggingface_hub import hf_hub_download
    p = hf_hub_download("tatsu-lab/alpaca_eval", "alpaca_farm_human_crossannotations.json", repo_type="dataset")
    rows = json.load(open(p))
    g = collections.defaultdict(list)
    meta = {}
    for r in rows:
        k = (r["instruction"], r["output_1"], r["output_2"])
        g[k].append(int(r["preference"]))
        meta[k] = r["dataset"]
    keys = sorted(g)
    random.Random(seed).shuffle(keys)
    items = []
    for n, k in enumerate(keys[:max_pairs] if max_pairs else keys):
        v = g[k]
        first = sum(x == 1 for x in v)
        lab = 1 if first * 2 > len(v) else 0 if first * 2 < len(v) else None
        pid = f"alpaca-{n:04d}"
        votes = ["first" if x == 1 else "second" for x in v]
        if lab is None:
            items.append(dict(id=f"{pid}|o0", pair_id=pid, group=pid, bench="alpacafarm", fmt="pair", order=0,
                              category=meta[k], gold=None, votes=votes, skip=True))
            continue
        items += _pair_items("alpacafarm", pid, pid, meta[k], k[1], k[2], lab, question=k[0], votes=votes,
                             examinee="unknown")
    return items


def load_mtbhuman(max_groups=400, seed=0, min_votes=1):
    """lmsys/mt_bench_human_judgments, human split: expert pairwise votes (model_a / model_b / tie) on MT-Bench
    conversations. Grouped by (question, model pair, turn). Gold = majority of non-tie votes; groups with no
    strict majority are kept for the label audit (gold None) and not judged."""
    from datasets import load_dataset
    d = load_dataset("lmsys/mt_bench_human_judgments", split="human")
    g = collections.defaultdict(list)
    conv = {}
    for r in d:
        a, b = r["model_a"], r["model_b"]
        key = (r["question_id"], tuple(sorted([a, b])), r["turn"])
        w = r["winner"]
        # store the vote relative to the sorted order (first model in key)
        if w == "tie":
            vote = "tie"
        else:
            winner_model = a if w == "model_a" else b
            vote = "first" if winner_model == key[1][0] else "second"
        g[key].append(vote)
        ca, cb = (r["conversation_a"], r["conversation_b"]) if a == key[1][0] else (r["conversation_b"], r["conversation_a"])
        conv[key] = (ca, cb)
    keys = sorted(k for k in g if len(g[k]) >= min_votes)
    random.Random(seed).shuffle(keys)
    items = []
    for key in keys[:max_groups]:
        v = g[key]
        f, s = v.count("first"), v.count("second")
        lab = 1 if f > s else 0 if s > f else None
        qid, (m1, m2), turn = key
        pid = f"mtbh-{qid}-{m1}-{m2}-t{turn}"
        ca, cb = conv[key]
        n_msgs = 2 * turn
        ca, cb = [dict(role=m["role"], content=m["content"]) for m in ca[:n_msgs]], \
                 [dict(role=m["role"], content=m["content"]) for m in cb[:n_msgs]]
        if lab is None:
            items.append(dict(id=f"{pid}|o0", pair_id=pid, group=f"mtbh-{qid}", bench="mtbhuman", fmt="pair",
                              order=0, category=str(qid), gold=None, votes=v, skip=True))
            continue
        items += _pair_items("mtbhuman", pid, f"mtbh-{qid}", str(qid), ca, cb, lab, votes=v, turn=turn,
                             examinee=f"{m1} vs {m2}", qid=qid)
    return items


def load_dpo5k():
    """stindardlogic/llm-judge-dpo-5k: 5,000 rows but only 15 distinct items. Used as a 15-item bias checklist:
    which of two critiques of the same response is more accurate and calibrated (gold = the 'chosen' one)."""
    from datasets import load_dataset
    d = load_dataset("stindardlogic/llm-judge-dpo-5k", split="train").to_pandas()
    d["category"] = d.metadata.apply(lambda m: m["category"])
    d["rejection_type"] = d.metadata.apply(lambda m: m["rejection_type"])
    d = d.drop_duplicates(["prompt", "chosen", "rejected"])
    items = []
    for n, r in enumerate(d.itertuples()):
        items += _pair_items("dpo5k", f"dpo-{n:02d}", f"dpo-{n:02d}", r.category, r.chosen, r.rejected, 1,
                             question=r.prompt, votes=None, examinee="synthetic", rejection_type=r.rejection_type)
    return items


LOADERS = dict(judgebench=load_judgebench, rb2=load_rb2, alpacafarm=load_alpacafarm, mtbhuman=load_mtbhuman,
               dpo5k=load_dpo5k)
