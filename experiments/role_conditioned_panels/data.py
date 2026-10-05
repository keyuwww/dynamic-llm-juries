"""Load the 8-judge pool judgments into (Z, Y, groups, ...).

Z (N x J, binary) is each judge's raw verdict, taken from the `votes` column. Y (N,) is the gold
human label. The match indicator 1[Z == Y] is deliberately NOT built here -- it lives only in
audit.py, and nothing that touches Z / eta-hat may import it.

Two benches share the same judgments schema:
  bff        BFF-Bench via the public kensho/VERDICTS dataset (what the spec targets)
  rb2safety  RewardBench-2 Safety via allenai/reward-bench-2 (stand-in when the BFF file is missing)
"""
import os
import re
import urllib.request
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Tinker list prices, $/call (spec's judge table; also Ingrid's COST_PER_CALL). Order = spec order.
COST_PER_CALL = {
    "gpt-oss-120b": 0.00072, "gpt-oss-20b": 0.00044, "deepseek-v3.1": 0.00261,
    "qwen3.6-35b-a3b": 0.00125, "qwen3.5-4b": 0.00073, "nemotron3-super-120b": 0.00095,
    "qwen3.5-9b": 0.00144, "nemotron3-nano-30b": 0.00029,
}
VERDICTS_URL = "https://huggingface.co/datasets/kensho/VERDICTS/resolve/main/data/train-00000-of-00001.parquet"
RB2_URL = "https://huggingface.co/datasets/allenai/reward-bench-2/resolve/main/data/test-00000-of-00001.parquet"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")


@dataclass
class Judgments:
    Z: np.ndarray            # (N, J) int8 judge verdicts, 1 = "correct"
    Y: np.ndarray            # (N,)  int8 gold human label
    groups: np.ndarray       # (N,)  question id, 0..G-1 (the unit of every split)
    judge_names: list
    cost: dict               # judge -> $/call
    examinee: np.ndarray
    prompt: np.ndarray
    response: np.ndarray
    item_ids: np.ndarray


def _fetch(url, name, path=None):
    if path:
        return pd.read_parquet(path)
    os.makedirs(CACHE_DIR, exist_ok=True)
    dest = os.path.join(CACHE_DIR, name)
    if not os.path.exists(dest):
        urllib.request.urlretrieve(url, dest)
    return pd.read_parquet(dest)


def _verdict(votes):
    """Keyu's convention: 'correct' only if a strict majority of votes say 1. Ties and unparseable
    votes (None) therefore give an 'incorrect' verdict."""
    votes = list(votes)
    return int(2 * sum(1 for v in votes if v == 1) > len(votes))


def _to_text(msgs):
    return "\n".join(f"{m.get('role')}: {m.get('content')}" for m in msgs)


def _text_bff(item_ids, verdicts_path):
    """Prompt = conversation up to the last assistant turn; response = that turn (as in the notebook)."""
    vd = _fetch(VERDICTS_URL, "verdicts.parquet", verdicts_path)
    if "dataset" in vd:
        vd = vd[vd["dataset"] == "bffbench"]
    vd = vd.assign(item_key=vd["cid"].astype(str) + "-t" + vd["turn"].astype(str)).drop_duplicates("item_key")
    vd = vd.set_index("item_key")

    def split_conv(conv):
        msgs = list(conv)
        last_a = max((i for i, m in enumerate(msgs) if m.get("role") == "assistant"), default=None)
        if last_a is None:
            return _to_text(msgs), ""
        return _to_text(msgs[:last_a]), str(msgs[last_a].get("content", ""))

    key = pd.Series(item_ids)
    cov = key.isin(vd.index).mean()
    assert cov > 0.9, f"item ids do not match VERDICTS (coverage {cov:.1%}); sample ids: {list(key[:3])}"
    pr = vd["conv"].map(split_conv)
    prompt = key.map({k: p for k, (p, _) in pr.items()}).fillna("").values
    response = key.map({k: r for k, (_, r) in pr.items()}).fillna("").values
    qid = key.map(vd["qid"]).astype(str).fillna("?").values
    return prompt, response, qid, cov


def _text_rb2(item_ids, rb2_path):
    rb = _fetch(RB2_URL, "rb2.parquet", rb2_path)
    rb = rb[rb["subset"] == "Safety"].set_index("id")
    prompt, response, qid = [], [], []
    for it in item_ids:
        m = re.match(r"rb2safety-(\d+)-(chosen|rejected)(\d+)$", it)
        assert m, f"unexpected rb2 item id {it}"
        rid, kind, i = m.group(1), m.group(2), int(m.group(3))
        row = rb.loc[rid] if rid in rb.index else rb.loc[int(rid)]
        p = row["prompt"]
        prompt.append(p if isinstance(p, str) else _to_text(list(p)))
        response.append(str(list(row[kind])[i]))
        qid.append(rid)
    return np.array(prompt), np.array(response), np.array(qid), 1.0


def load_judgments(path, bench="bff", condition="none", verdicts_path=None, rb2_path=None):
    raw = pd.read_json(path, lines=True)
    raw = raw[raw["condition"].astype(str).str.lower() == condition.lower()]
    if bench == "bff":
        raw = raw[~raw["item_id"].astype(str).str.startswith("rb2")]
    elif bench == "rb2safety":
        raw = raw[raw["item_id"].astype(str).str.startswith("rb2safety")]
    else:
        raise ValueError(bench)
    assert len(raw), (f"no rows for bench={bench!r}, condition={condition!r} in {path}. "
                      f"Judge file contents: {pd.read_json(path, lines=True)['item_id'].astype(str).str[:6].value_counts().to_dict()}")

    raw = raw.assign(z=raw["votes"].map(_verdict))
    Zdf = raw.pivot_table(index="item_id", columns="judge", values="z", aggfunc="max")
    unknown = [j for j in Zdf.columns if j not in COST_PER_CALL]
    assert not unknown, f"no price for judges {unknown}"
    judges = [j for j in COST_PER_CALL if j in Zdf.columns]
    Zdf = Zdf[judges].dropna()
    gold = raw.groupby("item_id")["gold"].agg(["min", "max"]).reindex(Zdf.index)
    assert (gold["min"] == gold["max"]).all(), "gold label differs across judge rows of an item"
    item_ids = np.array(Zdf.index.astype(str))
    Z = Zdf.values.astype(np.int8)
    Y = gold["min"].values.astype(np.int8)
    examinee = raw.groupby("item_id")["examinee"].first().reindex(Zdf.index).values

    # votes <-> vote_share consistency (where the judge actually parsed)
    chk = raw.dropna(subset=["vote_share"])
    assert ((chk["vote_share"] > 0.5).astype(int) == chk["z"]).all(), "Z from votes disagrees with vote_share"

    prompt, response, qid, cov = (_text_bff(item_ids, verdicts_path) if bench == "bff"
                                  else _text_rb2(item_ids, rb2_path))
    groups = pd.factorize(pd.Series(qid))[0]
    print(f"[data] bench={bench} condition={condition}: {Z.shape[0]} items x {Z.shape[1]} judges, "
          f"{groups.max() + 1} questions, text join coverage {cov:.1%}, mean(Y)={Y.mean():.3f}")
    return Judgments(Z=Z, Y=Y, groups=groups, judge_names=judges,
                     cost={j: COST_PER_CALL[j] for j in judges}, examinee=examinee,
                     prompt=prompt, response=response, item_ids=item_ids)


def drop_judges(d, exclude):
    """Return a copy of the Judgments restricted to the judges not in `exclude` (same items, same order)."""
    keep = [k for k, j in enumerate(d.judge_names) if j not in set(exclude)]
    assert len(keep) == len(d.judge_names) - len(set(exclude)), f"unknown judge in {exclude}"
    names = [d.judge_names[k] for k in keep]
    import dataclasses
    return dataclasses.replace(d, Z=d.Z[:, keep], judge_names=names, cost={j: d.cost[j] for j in names})
