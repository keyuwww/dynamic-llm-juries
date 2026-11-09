"""Items for the three benchmarks. Each item: dict(item_id, group, input, response, gold) with gold = 1 if the response is correct per the human label
(BFF, RewardBench-2 Safety), or dict(item_id, group, input, response_1, response_2, gold in {'A','B'}) for JudgeBench pairs."""
import os, re, urllib.request
import pandas as pd

VERDICTS_URL = "https://huggingface.co/datasets/kensho/VERDICTS/resolve/main/data/train-00000-of-00001.parquet"
RB2_URL = "https://huggingface.co/datasets/allenai/reward-bench-2/resolve/main/data/test-00000-of-00001.parquet"
JB_URL = "https://huggingface.co/datasets/ScalerLab/JudgeBench/resolve/main/data/{}-00000-of-00001.jsonl"


def render_conv(conv):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in conv)


def fetch(url, name, path=None):
    if path:
        return path
    dest = os.path.join(os.path.expanduser("~"), ".cache", "caljudges", name); os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        urllib.request.urlretrieve(url, dest)
    return dest


def gold_labels(judgments, bench, condition="none"):
    """item ids (the items on which all pool judges have a verdict, as in the earlier analyses) and the human label of each."""
    raw = pd.read_json(judgments, lines=True); raw = raw[raw["condition"].astype(str).str.lower() == condition]
    raw = raw[raw["item_id"].astype(str).str.startswith("rb2safety")] if bench == "rb2safety" else raw[~raw["item_id"].astype(str).str.startswith("rb2")]
    ok = raw.pivot_table(index="item_id", columns="judge", values="gold", aggfunc="first").dropna().index
    g = raw.groupby("item_id")["gold"].first().reindex(ok)
    return [str(i) for i in ok], [int(float(x)) for x in g.values]


PPE_CORRECT = ["PPE-MMLU-Pro-Best-of-K", "PPE-MATH-Best-of-K", "PPE-GPQA-Best-of-K", "PPE-MBPP-Plus-Best-of-K", "PPE-IFEval-Best-of-K"]
PPE_N = 7000                                    # items per PPE kind: the paper trains on 4,000 (2,000 correctness + 2,000 preference) and evaluates on ~10K held-out; we take 7,000 + 7,000 and split by question


def _ppe_read(repo):
    """download a PPE dataset from the Hugging Face hub (public) and return it as one dataframe"""
    import glob
    from huggingface_hub import snapshot_download
    d = snapshot_download(repo_id=f"lmarena-ai/{repo}", repo_type="dataset", allow_patterns=["*.parquet"])
    return pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(d, "**", "*.parquet"), recursive=True))], ignore_index=True)


def load_ppe(kind, n=PPE_N, seed=0):
    """Pairwise items from the paper's training data (PPE, Frick et al. 2024), format like JudgeBench: dict(item_id, group, input, response_1, response_2, gold in {'A','B'}).
      ppe_correct: the 5 verifiable-correctness sets (MMLU-Pro, MATH, GPQA, MBPP-Plus, IFEval); a pair = one correct and one incorrect response of the same question
                   (the dataset's own `sampled_conflict_pairs`, 5 per question); gold = the correct one.
      ppe_pref   : human preference (Chatbot Arena), pairs with a winner; gold = the winner.
    A fixed random sample of n items (seed 0); group = the question, so splits can be made by question."""
    import numpy as np
    rng = np.random.default_rng(seed); out = []
    if kind == "ppe_correct":
        for repo in PPE_CORRECT:
            df = _ppe_read(repo); tag = repo.replace("PPE-", "").replace("-Best-of-K", "")
            for r in df.itertuples():
                sc = list(r.scores); q = str(getattr(r, "question", None) or getattr(r, "problem", None) or getattr(r, "prompt"))
                for k, (i, j) in enumerate(r.sampled_conflict_pairs):
                    if bool(sc[i]) == bool(sc[j]):
                        continue
                    out.append(dict(item_id=f"{tag}-{r.question_id}-{k}", group=f"{tag}-{r.question_id}", input=str(r.prompt), response_1=str(getattr(r, f"response_{i + 1}")),
                                    response_2=str(getattr(r, f"response_{j + 1}")), gold="A" if bool(sc[i]) else "B", source=tag))
    else:
        df = _ppe_read("PPE-Human-Preference-V1"); df = df[df["winner"].isin(["model_a", "model_b"])]
        for k, r in enumerate(df.itertuples()):
            out.append(dict(item_id=f"pref-{r.question_id}-{k}", group=f"pref-{r.question_id}", input=str(r.prompt), response_1=str(r.response_1), response_2=str(r.response_2),
                            gold="A" if r.winner == "model_a" else "B", source="human-preference"))
    idx = rng.permutation(len(out))[:n]
    return [out[i] for i in idx]                  # random order, so the first N items are a random subset (used for the n-sample baselines)


def load_items(bench, judgments=None, verdicts_path=None, rb2_path=None, jb_dir=None):
    if bench in ("ppe_correct", "ppe_pref"):
        return load_ppe(bench)
    if bench == "judgebench":
        out = []
        for split in ("gpt", "claude"):
            p = os.path.join(jb_dir, f"{split}.jsonl") if jb_dir else fetch(JB_URL.format(split), f"jb_{split}.jsonl")
            for r in pd.read_json(p, lines=True).itertuples():
                out.append(dict(item_id=str(r.pair_id), group=str(r.original_id) + "|" + split, input=str(r.question), response_1=str(r.response_A), response_2=str(r.response_B), gold="A" if r.label.startswith("A>") else "B", source=r.source))
        return out
    ids, gold = gold_labels(judgments, bench); out = []
    if bench == "bff":
        vd = pd.read_parquet(fetch(VERDICTS_URL, "verdicts.parquet", verdicts_path)); vd = vd[vd["dataset"] == "bffbench"] if "dataset" in vd else vd
        vd = vd.assign(key=vd["cid"].astype(str) + "-t" + vd["turn"].astype(str)).drop_duplicates("key").set_index("key")
        for i, g in zip(ids, gold):
            row = vd.loc[i]; msgs = [dict(role=m["role"], content=m["content"]) for m in list(row["conv"])]
            last_a = max(k for k, m in enumerate(msgs) if m["role"] == "assistant")
            out.append(dict(item_id=i, group=str(row["qid"]), input=render_conv(msgs[:last_a]), response=msgs[last_a]["content"], gold=g))
    else:
        rb = pd.read_parquet(fetch(RB2_URL, "rb2.parquet", rb2_path)); rb = rb[rb["subset"] == "Safety"].copy(); rb["id"] = rb["id"].astype(str); rb = rb.set_index("id")
        for i, g in zip(ids, gold):
            m = re.match(r"rb2safety-(\d+)-(chosen|rejected)(\d+)$", i); rid, kind, k = m.group(1), m.group(2), int(m.group(3)); row = rb.loc[rid]
            out.append(dict(item_id=i, group=rid, input=str(row["prompt"]), response=str(list(row[kind])[k]), gold=g))
    return out
