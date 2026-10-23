"""Stage C analyses on the new confidence runs (results/confidence/...).

C2  controlled BFF pairs (data/bffctrl_items.json):
      identical  same answer in both slots: share of judges' picks driven purely by position
      corrupt    answer vs the same answer with one figure changed +10%: accuracy, flip rate, confident errors,
                 stated confidence when wrong; compared with the judge's flip rate on real BFF pairs
      pad        answer vs the same answer plus a neutral paragraph: preference for the longer version
C4  single-answer grading (RewardBench 2 other, 'rb2'): with no order to swap, do other judges' disagreement and
    low stated confidence flag the best judge's errors, and does that add to its own confidence?
Usage: python stage_c.py -> results/flips/stage_c.md (+ .json)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from flip_analysis import boot_auc, catch_at_rate  # noqa: E402
from order_consistency import POOL, auroc  # noqa: E402

OUT = HERE / "results" / "flips"
SHORT = {"gpt-oss-120b": "oss-120b", "gpt-oss-20b": "oss-20b", "deepseek-v3.1": "deepseek", "qwen3.6-35b-a3b": "qwen-35b",
         "qwen3.5-9b": "qwen-9b", "qwen3.5-4b": "qwen-4b", "nemotron3-super-120b": "nem-super", "nemotron3-nano-30b": "nem-nano"}


def rows(bench):
    p = HERE / "results" / "confidence" / bench / "judgments.jsonl"
    return pd.DataFrame([json.loads(l) for l in open(p)]) if p.exists() else pd.DataFrame()


def c2():
    t = rows("bffctrl")
    if t.empty:
        return None, []
    items = {o["id"]: o for o in json.load(open(HERE / "data" / "bffctrl_items.json"))}
    t["pair_id"] = t.item_id.map(lambda i: items[i]["pair_id"])
    t["order"] = t.item_id.map(lambda i: items[i]["order"])
    t["condition"] = t.item_id.map(lambda i: items[i]["condition"])
    real = rows("bffpair")
    real_flip = {}
    if not real.empty:
        real["pair_id"] = real.item_id.str.rsplit("|", n=1).str[0]
        real["order"] = real.item_id.str.rsplit("|", n=1).str[1]
        for j, x in real.groupby("judge"):
            w = x.pivot_table(index="pair_id", columns="order", values="verdict").dropna()
            real_flip[j] = float((w["ab"] == w["ba"]).mean())
    out = []
    for j, x in t.groupby("judge"):
        r = dict(judge=j)
        for cond in ["identical", "corrupt", "pad"]:
            y = x[x.condition == cond]
            w = y.pivot_table(index="pair_id", columns="order", values="verdict").dropna()
            cf = y.pivot_table(index="pair_id", columns="order", values="conf")
            if w.empty:
                continue
            same_pos = (w["ab"] == w["ba"])                      # picked the same position both times
            if cond == "identical":
                r["identical_first_both"] = float(((w["ab"] == 1) & (w["ba"] == 1)).mean())
                r["identical_second_both"] = float(((w["ab"] == 0) & (w["ba"] == 0)).mean())
                r["identical_conf"] = float(cf.mean(1).mean())
            elif cond == "corrupt":
                # ab: original first (gold 1); ba: original second (gold 0)
                right_ab, right_ba = (w["ab"] == 1), (w["ba"] == 0)
                r["corrupt_acc"] = float((right_ab.mean() + right_ba.mean()) / 2)
                r["corrupt_flip"] = float(same_pos.mean())
                r["corrupt_conf_wrong"] = float((~right_ab & ~right_ba).mean())
                c = cf.reindex(w.index).mean(1)
                both_right = right_ab & right_ba
                r["corrupt_conf_if_right"] = float(c[both_right].mean())
                r["corrupt_conf_if_wrong_both"] = float(c[~right_ab & ~right_ba].mean()) if (~right_ab & ~right_ba).any() else np.nan
            else:
                # ab: padded first; ba: padded second
                r["pad_prefers_long_both"] = float(((w["ab"] == 1) & (w["ba"] == 0)).mean())
                r["pad_prefers_short_both"] = float(((w["ab"] == 0) & (w["ba"] == 1)).mean())
                r["pad_flip"] = float(same_pos.mean())
        r["real_bff_flip"] = real_flip.get(j, np.nan)
        out.append(r)
    T = pd.DataFrame(out).set_index("judge").reindex([j for j in POOL if j in set(t.judge)])
    T.index = T.index.map(SHORT)
    L = ["## C2. Controlled BFF pairs", "",
         f"{t.pair_id.nunique()} pairs ({(t.condition == 'identical').sum() // 16} identical, "
         f"{(t.condition == 'corrupt').sum() // 16} corrupted, {(t.condition == 'pad').sum() // 16} padded per judge), "
         "both orders, 8 judges.", "",
         "- **identical**: same answer in both slots. `first_both` / `second_both` = picked the same position in both "
         "orders (pure position preference).",
         "- **corrupt**: original vs the same answer with its last figure changed by +10%. `flip` = picked the same "
         "position both times; `conf_wrong` = picked the corrupted answer in both orders.",
         "- **pad**: original vs the same answer plus a neutral paragraph.", "",
         (100 * T[[c for c in T.columns if not c.endswith("_conf") and "conf_if" not in c]]).round(1).to_markdown(), "",
         "Stated confidence on corrupted pairs (mean of both orders): " + ", ".join(
             f"{i} right {r.corrupt_conf_if_right:.0f} / wrong-both {r.corrupt_conf_if_wrong_both:.0f}"
             for i, r in T.iterrows() if not np.isnan(r.get("corrupt_conf_if_wrong_both", np.nan))) + ".", ""]
    return T.round(4).reset_index().to_dict(orient="records"), L


def c4():
    t = rows("rb2")
    if t.empty:
        return None, []
    it = pd.read_pickle(HERE / "data" / "rb2_items.pkl").set_index("key")
    t["group"] = t.item_id.map(it.group).astype(str)
    t["right"] = (t.verdict == t.gold).astype(float).where(t.verdict.notna(), 0.0)
    acc = t.groupby("judge").right.mean()
    target = acc.idxmax()
    V = t.pivot_table(index="item_id", columns="judge", values="verdict")
    C = t.pivot_table(index="item_id", columns="judge", values="conf")
    Pv = t.pivot_table(index="item_id", columns="judge", values="p_verdict")
    R = t.pivot_table(index="item_id", columns="judge", values="right")
    others = [j for j in V.columns if j != target]
    ok = V[target].notna()
    y = (R.loc[ok, target] == 0).values.astype(int)
    g = t.drop_duplicates("item_id").set_index("item_id").group.reindex(V.index[ok]).values
    dis = (V.loc[ok, others].ne(V.loc[ok, target], axis=0) & V.loc[ok, others].notna()).sum(1).values.astype(float)
    low_conf_others = (-C.loc[ok, others]).rank(pct=True).mean(1).fillna(0.5).values
    own_stated = (-C.loc[ok, target].fillna(C[target].median())).rank(pct=True).values
    own_token = (-Pv.loc[ok, target].fillna(Pv[target].median())).rank(pct=True).values
    dis_r = pd.Series(dis).rank(pct=True).values
    comb = (own_stated + dis_r) / 2
    comb3 = (own_stated + dis_r + low_conf_others) / 3
    sig = {"own stated confidence (low)": own_stated, "own token probability (low)": own_token,
           "others disagreeing (count)": dis, "others' low stated confidence": low_conf_others,
           "own confidence + others disagreeing": comb, "own + disagreeing + others' low confidence": comb3}
    res = dict(target=target, n=int(ok.sum()), errors=int(y.sum()), error_rate=float(y.mean()),
               acc={SHORT[k]: float(v) for k, v in acc.items()},
               signals={k: dict(auroc=boot_auc(y, v, g), catch18=catch_at_rate(v, y, .18)) for k, v in sig.items()})
    L = ["## C4. Single-answer grading (RewardBench 2 other)", "",
         f"Best judge {target}; {res['n']} items, {res['errors']} errors ({100 * res['error_rate']:.1f}%). No order to "
         "swap, so the cross-judge signal is plain disagreement plus the other judges' stated confidence.", "",
         "| Signal | AUROC [95% CI] | Errors caught at 18% flagged |", "|---|---|---|"] + [
        f"| {k} | {v['auroc'][0]:.2f} [{v['auroc'][1]:.2f}, {v['auroc'][2]:.2f}] | {100 * v['catch18']:.0f}% |"
        for k, v in res["signals"].items()] + [""]
    return res, L


def main():
    a, la = c2()
    b, lb = c4()
    (OUT / "stage_c.json").write_text(json.dumps(dict(c2=a, c4=b), indent=1, default=float))
    txt = "\n".join(["# Stage C: controlled pairs and single-answer grading", ""] + la + lb)
    (OUT / "stage_c.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
