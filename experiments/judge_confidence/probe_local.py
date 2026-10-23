#!/usr/bin/env python3
"""
Step 2.3 (local): read a small open judge's hidden states on original vs edited BFF answers.

The judge (default Qwen/Qwen3.5-4B, thinking off) sees the same grading prompt as the Tinker judges, but must answer
immediately: the assistant turn is pre-filled with "VERDICT:", so one forward pass gives both
  - the verdict probability P(CORRECT) from the next-token logits, and
  - the residual stream at every layer, saved at three positions:
      target  the last token of the edited span (for ORIG: the same span before editing, one per paired variant)
      end     the last token of the answer
      verdict the last prompt token (where the verdict is produced)

Raw outputs (git-ignored, kept for reuse): results/raw/activations/<model>/
  index.jsonl                  one row per (text, condition): positions, token strings, P(CORRECT), top-10 next tokens
  <text>__<cond>.npy           float16 array (n_positions, n_layers + 1, hidden)

  python experiments/judge_confidence/probe_local.py --limit-items 30
  python experiments/judge_confidence/probe_local.py --analyze
"""
import argparse, json, re

import numpy as np

from jc_common import HERE, RAW, REPO, load_bff_correct
import sys
sys.path.insert(0, str(REPO / "experiments" / "tinker_pool"))
from run_judges import BFF_JUDGE, REF_BLOCK, render_conv  # noqa: E402

DIRECT = BFF_JUDGE.replace('Reason briefly, then end with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT".',
                           'Answer with exactly one line: "VERDICT: CORRECT" or "VERDICT: INCORRECT".')
CONDS = ("none", "human")


def safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)


def load_texts(limit_items=None):
    """ORIG + passing variants, with the character span of the edit in each text."""
    items = {it["id"]: it for it in load_bff_correct()}
    var = [json.loads(l) for l in open(RAW / "variants.jsonl")]
    seen = []
    for v in var:
        if v["item_id"] not in seen:
            seen.append(v["item_id"])
    keep = set(seen[:limit_items]) if limit_items else set(seen)
    out = {}
    for v in var:
        if not v.get("ok") or v["item_id"] not in keep:
            continue
        it = items[v["item_id"]]
        e = (v["proposal"].get("edits") or [{}])[0]
        new_at = v["new"].find(e.get("new", "")) if e.get("new") else -1
        old_at = v["original"].find(e.get("old", "")) if e.get("old") else -1
        out[f"{it['id']}|{v['vtype']}"] = dict(it=it, vtype=v["vtype"], answer=v["new"],
                                               spans={v["vtype"]: (new_at, new_at + len(e.get("new", "")))})
        o = out.setdefault(f"{it['id']}|ORIG", dict(it=it, vtype="ORIG", answer=v["original"], spans={}))
        o["spans"][v["vtype"]] = (old_at, old_at + len(e.get("old", "")))
    return out


def build_messages(it, answer, cond):
    conv = it["conv"][:-1] + [{"role": "assistant", "content": answer}]
    ref = "" if cond == "none" else REF_BLOCK.format(note=" (written by an expert)", ref=it["ref"])
    return [{"role": "user", "content": DIRECT.format(conversation=render_conv(conv), reference=ref)}]


def run(a):
    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer
    out_dir = RAW / "activations" / safe(a.model.split("/")[-1].lower())
    out_dir.mkdir(parents=True, exist_ok=True)
    idx_path = out_dir / "index.jsonl"
    done = set()
    if idx_path.exists():
        done = {json.loads(l)["key"] for l in open(idx_path)}
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16).to(a.device).eval()
    cand = {w: tok.encode(w, add_special_tokens=False)[0] for w in (" CORRECT", " INCORRECT")}
    texts = load_texts(a.limit_items)
    print(f"{len(texts)} texts x {len(CONDS)} conditions; model {a.model} on {a.device}", flush=True)
    fh = open(idx_path, "a")
    n = 0
    for tid, t in sorted(texts.items()):
        for cond in CONDS:
            key = f"{tid}|{cond}"
            if key in done:
                continue
            prompt = tok.apply_chat_template(build_messages(t["it"], t["answer"], cond), tokenize=False,
                                             add_generation_prompt=True, enable_thinking=False) + "VERDICT:"
            enc = tok(prompt, return_offsets_mapping=True, return_tensors="pt")
            offs = enc.pop("offset_mapping")[0].tolist()
            a_start = prompt.find(t["answer"])
            pos, names = [], []
            for vt, (s, e) in sorted(t["spans"].items()):
                if s < 0 or a_start < 0:
                    continue
                ce = a_start + e - 1  # last character of the edited span
                ti = next((i for i, (x, y) in enumerate(offs) if x <= ce < y), None)
                if ti is not None:
                    pos.append(ti), names.append(f"target:{vt}")
            ae = a_start + len(t["answer"]) - 1
            ti = next((i for i, (x, y) in enumerate(offs) if x <= ae < y), None)
            if ti is not None:
                pos.append(ti), names.append("end")
            pos.append(len(offs) - 1), names.append("verdict")
            with torch.no_grad():
                # logits only at the last position: full-vocabulary logits for every token would take GBs
                o = model(**{k: v.to(a.device) for k, v in enc.items()}, output_hidden_states=True,
                          logits_to_keep=1, use_cache=False)
            hs = torch.stack([h[0, pos, :] for h in o.hidden_states], dim=1)  # (n_pos, layers+1, hidden)
            logits = o.logits[0, -1].float()
            lp = torch.log_softmax(logits, -1)
            l_c, l_i = lp[cand[" CORRECT"]].item(), lp[cand[" INCORRECT"]].item()
            top = torch.topk(lp, 10)
            fname = f"{safe(tid)}__{cond}.npy"
            np.save(out_dir / fname, hs.to(torch.float16).cpu().numpy())
            fh.write(json.dumps(dict(key=key, text_id=tid, item_id=t["it"]["id"], vtype=t["vtype"], condition=cond,
                                     gold=1 if t["vtype"] in ("ORIG", "C1", "C2") else 0, file=fname,
                                     positions=dict(zip(names, pos)), n_tokens=len(offs),
                                     tokens={nm: tok.decode(enc["input_ids"][0, p]) for nm, p in zip(names, pos)},
                                     logp_correct=l_c, logp_incorrect=l_i,
                                     p_correct=float(np.exp(l_c) / (np.exp(l_c) + np.exp(l_i))),
                                     top10=[(tok.decode([i]), float(v)) for v, i in zip(top.values.tolist(),
                                                                                     top.indices.tolist())],
                                     model=a.model)) + "\n")
            fh.flush()
            n += 1
            if n % 20 == 0:
                print(f"  {n} done", flush=True)
    print(f"done: {n} new rows in {out_dir}", flush=True)


def analyze(a):
    """Layer-wise logistic probes for 'this text contains an injected error', cross-validated by item, at each
    position; compared with the judge's own verdict on the same texts."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    out_dir = RAW / "activations" / safe(a.model.split("/")[-1].lower())
    rows = [json.loads(l) for l in open(out_dir / "index.jsonl")]
    res = {}
    for cond in CONDS:
        rs = [r for r in rows if r["condition"] == cond]
        y = np.array([1 - r["gold"] for r in rs])  # 1 = contains an error
        groups = np.array([r["item_id"] for r in rs])
        verdict_auc = roc_auc_score(y, [1 - r["p_correct"] for r in rs]) if 0 < y.mean() < 1 else None
        res[cond] = dict(n=len(rs), verdict_auroc=verdict_auc, positions={})
        for pname in ("target", "end", "verdict"):
            X, keep = [], []
            for i, r in enumerate(rs):
                arr = np.load(out_dir / r["file"]).astype(np.float32)
                names = list(r["positions"])
                if pname == "target":
                    # variant: its own edit; ORIG: the first paired span
                    ks = [k for k in names if k.startswith("target:")]
                    if not ks:
                        continue
                    j = names.index(ks[0])
                else:
                    j = names.index(pname)
                X.append(arr[j]), keep.append(i)
            X = np.stack(X)  # (n, layers+1, hidden)
            yy, gg = y[keep], groups[keep]
            aucs = []
            for L in range(X.shape[1]):
                pred = np.zeros(len(yy))
                for tr, te in GroupKFold(n_splits=5).split(X[:, L], yy, gg):
                    clf = LogisticRegression(C=0.05, max_iter=2000).fit(X[tr, L], yy[tr])
                    pred[te] = clf.predict_proba(X[te, L])[:, 1]
                aucs.append(roc_auc_score(yy, pred))
            bl = int(np.argmax(aucs))
            pred = np.zeros(len(yy))
            for tr, te in GroupKFold(n_splits=5).split(X[:, bl], yy, gg):
                clf = LogisticRegression(C=0.05, max_iter=2000).fit(X[tr, bl], yy[tr])
                pred[te] = clf.predict_proba(X[te, bl])[:, 1]
            # per variant type: AUROC of (this type vs ORIG) for the probe and for the verdict
            vt = np.array([rs[i]["vtype"] for i in keep])
            pv = np.array([1 - rs[i]["p_correct"] for i in keep])
            per = {}
            for t in sorted(set(vt) - {"ORIG"}):
                m = (vt == t) | (vt == "ORIG")
                yt = (vt[m] == t).astype(int)
                per[t] = dict(n=int((vt == t).sum()), probe_auroc=float(roc_auc_score(yt, pred[m])),
                              verdict_auroc=float(roc_auc_score(yt, pv[m])),
                              verdict_says_incorrect=float(np.mean(pv[vt == t] > 0.5)))
            res[cond]["positions"][pname] = dict(auroc_by_layer=aucs, best_layer=bl, best_auroc=float(max(aucs)),
                                                 by_type=per)
        print(cond, "verdict AUROC", res[cond]["verdict_auroc"],
              {p: round(v["best_auroc"], 3) for p, v in res[cond]["positions"].items()})
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"probe_{safe(a.model.split('/')[-1].lower())}.json").write_text(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--limit-items", type=int, default=None)
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    analyze(a) if a.analyze else run(a)


if __name__ == "__main__":
    main()
