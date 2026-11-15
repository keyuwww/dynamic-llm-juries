#!/usr/bin/env python3
"""
Switch-off test (drill-down Step 3): do the heads the module map flagged really carry the Safety "knows" signal?

The module map (module_map.py) split the layer-16 probe score into one share per head / MLP. That is a reading, not a
cause. Here we switch parts off and watch what happens:

  switch off   replace the part's output at the verdict position with its average over all questions of that
               benchmark, so it still sends a normal-looking signal but can no longer tell good from bad answers
  boost        the opposite: double how far the part's output sits from its average

Jobs (names use 1-based layers and heads, as in the report):
  base               nothing switched off
  S_right            the three biggest right-answer heads: L16 h2, L16 h5, L8 h4         (Safety + BFF)
  S_wrong            the two biggest wrong-answer heads:   L8 h3, L16 h8                 (Safety + BFF)
  rand3_i / rand2_i  19 random sets of 3 / 2 heads from layers 1-16 (the fair "luck" comparison)
  S_right_boost / S_wrong_boost
  single_*           each of the 8 biggest Safety parts alone (heads and MLPs)
  bff_mlp_L          each MLP in layers 1-19 alone, on BFF (is BFF's L19 MLP special?)

What we measure, per benchmark, on every item:
  knows   AUROC of a FIXED probe trained on the normal model (5-fold cross-fitted, so every item is scored by a probe
          that never saw it), read at every layer; the main number is the module map's reference layer
          (Safety 16, BFF 19) and a later layer (Safety 20, BFF 22)
  says    AUROC of the forced verdict P(CORRECT)
both as same-source AUROC (within resp_model|refusal for Safety, examinee for BFF), like the rest of the study.

  .venv/bin/python experiments/weight_space/switch_off.py build
  modal run experiments/weight_space/switch_off.py --limit 6        # smoke test
  modal run experiments/weight_space/switch_off.py
  .venv/bin/python experiments/weight_space/switch_off.py analyze
"""
import argparse, json, sys
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

try:
    import modal
except ImportError:
    modal = None

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "raw" / "switch_off"
MM = HERE / "results" / "raw" / "module_map"
POS_ID, NEG_ID = 25619, 17579          # " CORRECT" / " INCORRECT" first tokens (both benchmarks)
NREP = 19
REF = {"safety": 16, "bff": 19}
LATE = {"safety": 20, "bff": 22}


# ----------------------------------------------------------------------------- GPU side
def run_remote(jobs: list, data: dict) -> list:
    import numpy as np
    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")
    model = AutoModelForImageTextToText.from_pretrained("Qwen/Qwen3.5-0.8B", dtype=torch.bfloat16).to("cuda").eval()
    lm = model.model.language_model
    nheads = data["nheads"]
    active = {}   # (kind, layer0) -> list of (slice, mean tensor); mode in active["_mode"]

    def hook(key):
        def f(mod, args):
            todo = active.get(key)
            if not todo:
                return None
            x = args[0].clone()
            for sl, mu in todo:
                cur = x[0, -1, sl].float()
                new = mu if active["_mode"] == "mean" else mu + 2.0 * (cur - mu)
                x[0, -1, sl] = new.to(x.dtype)
            return (x,) + tuple(args[1:])
        return f
    for i, L in enumerate(lm.layers):
        mix = L.linear_attn.out_proj if hasattr(L, "linear_attn") else L.self_attn.o_proj
        mix.register_forward_pre_hook(hook(("head", i)))
        L.mlp.down_proj.register_forward_pre_hook(hook(("mlp", i)))

    enc = {}
    for b, texts in data["texts"].items():
        enc[b] = []
        for t in texts:
            p = tok.apply_chat_template([{"role": "user", "content": t}], tokenize=False, add_generation_prompt=True,
                                        enable_thinking=False) + "VERDICT:"
            enc[b].append(tok(p, return_tensors="pt", truncation=True, max_length=8192)["input_ids"])
    probes = {b: (torch.as_tensor(np.frombuffer(v["W"], np.float32).reshape(5, 25, 1024).copy(), device="cuda"),
                  torch.as_tensor(np.frombuffer(v["b"], np.float32).reshape(5, 25).copy(), device="cuda"),
                  v["fold"]) for b, v in data["probes"].items()}
    means = {b: (np.frombuffer(v["mix"], np.float32).reshape(24, 2048), np.frombuffer(v["mlp"], np.float32).reshape(24, 3584))
             for b, v in data["means"].items()}

    res = []
    for j in jobs:
        r = dict(name=j["name"])
        for b in j["benches"]:
            active.clear()
            active["_mode"] = j["mode"]
            Mmix, Mmlp = means[b]
            for kind, l, h in j["comps"]:
                if kind == "head":
                    d = 2048 // nheads[l]
                    sl = slice(h * d, (h + 1) * d)
                    mu = torch.as_tensor(Mmix[l, sl].copy(), device="cuda")
                else:
                    sl = slice(0, 3584)
                    mu = torch.as_tensor(Mmlp[l].copy(), device="cuda")
                active.setdefault((kind, l), []).append((sl, mu))
            W, B, fold = probes[b]
            P, K = [], []
            for n, ids in enumerate(enc[b]):
                with torch.no_grad():
                    o = model(input_ids=ids.to("cuda"), output_hidden_states=True, logits_to_keep=1, use_cache=False)
                lg = o.logits[0, -1].float()
                P.append(float(torch.sigmoid(lg[POS_ID] - lg[NEG_ID])))
                hs = torch.stack([h[0, -1] for h in o.hidden_states]).float()      # (25, 1024)
                K.append(((hs * W[fold[n]]).sum(-1) + B[fold[n]]).cpu().numpy().round(4).tolist())
            r[b] = dict(p=P, k=K)
        active.clear()
        res.append(r)
        print(j["name"], "done", flush=True)
    return res


def main(limit: int = 0, per: int = 3):
    import pickle
    jobs = pickle.loads((OUT / "jobs.pkl").read_bytes())
    data = pickle.loads((OUT / "data.pkl").read_bytes())
    if limit:
        keep = {"base", "S_right", "single_L16h2", "bff_mlp_19"}
        jobs = [j for j in jobs if j["name"] in keep]
        for b in data["texts"]:
            data["texts"][b] = data["texts"][b][:limit]
    # Safety-heavy jobs first so the slowest containers start early
    jobs.sort(key=lambda j: -sum(len(data["texts"][b]) for b in j["benches"]))
    chunks = [jobs[i:i + per] for i in range(0, len(jobs), per)]
    print(f"{len(jobs)} jobs in {len(chunks)} containers", flush=True)
    res = []
    for r in run_remote.starmap([(c, data) for c in chunks]):
        res += r
    (OUT / ("smoke_results.json" if limit else "results.json")).write_text(json.dumps(res))
    print("saved", len(res))


if modal is not None:
    image = (modal.Image.debian_slim(python_version="3.12")
             .pip_install("torch==2.15.0", "transformers==5.22.2", "numpy==2.5.4")
             .env({"HF_HOME": "/root/.cache/huggingface"}))
    hf_cache = modal.Volume.from_name("dlj-hf-cache", create_if_missing=True)
    app = modal.App("weight-space-switch-off", image=image)
    run_remote = app.function(gpu=["L4", "A10G", "L40S", "A100-40GB"], timeout=3600,
                              volumes={"/root/.cache/huggingface": hf_cache})(run_remote)
    main = app.local_entrypoint()(main)


# ----------------------------------------------------------------------------- build jobs (local)
def load(c):
    items = [json.loads(l) for l in open(MM / c / "items.jsonl")]
    Z = np.load(MM / c / "acts.npz")
    y = np.array([it["gold"] for it in items])
    g = np.array([it["group"] for it in items])
    strata = np.array([f"{it['resp_model']}|{it['refusal']}" if c == "safety" else it["examinee"] for it in items])
    return items, Z, y, g, strata


def build(a):
    import pickle
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler
    mm = json.loads((HERE / "results" / "module_map.json").read_text())
    nheads = mm["nheads"]
    rng = np.random.default_rng(0)
    data = dict(nheads=nheads, texts={}, probes={}, means={})
    for c in ("safety", "bff"):
        items, Z, y, g, _ = load(c)
        HS = Z["hs"].astype(np.float32)
        fold = np.zeros(len(y), int)
        W = np.zeros((5, 25, 1024), np.float32)
        B = np.zeros((5, 25), np.float32)
        for f, (tr, te) in enumerate(GroupKFold(5).split(HS, y, g)):
            fold[te] = f
            for L in range(1, 25):
                sc = StandardScaler().fit(HS[tr, L])
                lr = LogisticRegression(C=0.3, max_iter=3000).fit(sc.transform(HS[tr, L]), y[tr])
                W[f, L] = lr.coef_[0] / sc.scale_
                B[f, L] = lr.intercept_[0] - (lr.coef_[0] * sc.mean_ / sc.scale_).sum()
        data["texts"][c] = [it["text"] for it in items]
        data["probes"][c] = dict(W=W.tobytes(), b=B.tobytes(), fold=fold.tolist())
        data["means"][c] = dict(mix=Z["mix"].astype(np.float32).mean(0).tobytes(),
                                mlp=Z["mlp"].astype(np.float32).mean(0).tobytes())
        print(c, "probes fit", flush=True)

    def H(l, h):   # 1-based -> 0-based
        return ("head", l - 1, h - 1)
    right = [H(16, 2), H(16, 5), H(8, 4)]
    wrong = [H(8, 3), H(16, 8)]
    pool = [("head", l, h) for l in range(16) for h in range(nheads[l]) if ("head", l, h) not in right + wrong]
    both, S = ["safety", "bff"], ["safety"]
    jobs = [dict(name="base", family="base", comps=[], mode="mean", benches=both),
            dict(name="S_right", family="group", comps=right, mode="mean", benches=both),
            dict(name="S_wrong", family="group", comps=wrong, mode="mean", benches=both),
            dict(name="S_right_boost", family="boost", comps=right, mode="boost", benches=S),
            dict(name="S_wrong_boost", family="boost", comps=wrong, mode="boost", benches=S)]
    for i in range(NREP):
        jobs.append(dict(name=f"rand3_{i}", family="rand3", mode="mean", benches=both,
                         comps=[pool[k] for k in rng.choice(len(pool), 3, replace=False)]))
        jobs.append(dict(name=f"rand2_{i}", family="rand2", mode="mean", benches=S,
                         comps=[pool[k] for k in rng.choice(len(pool), 2, replace=False)]))
    rows = [r for r in mm["safety"]["rows"] if r["kind"] != "emb"]
    for r in sorted(rows, key=lambda r: -abs(r["share"]))[:8]:
        nm = f"L{r['layer']}h{r['head']}" if r["kind"] == "head" else f"L{r['layer']}mlp"
        comp = H(r["layer"], r["head"]) if r["kind"] == "head" else ("mlp", r["layer"] - 1, -1)
        jobs.append(dict(name=f"single_{nm}", family="single", comps=[comp], mode="mean", benches=S,
                         share=r["share"]))
    for L in range(1, 20):
        jobs.append(dict(name=f"bff_mlp_{L}", family="bff_mlp", comps=[("mlp", L - 1, -1)], mode="mean",
                         benches=["bff"]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "jobs.pkl").write_bytes(pickle.dumps(jobs))
    (OUT / "data.pkl").write_bytes(pickle.dumps(data))
    (OUT / "meta.json").write_text(json.dumps(jobs))
    n = sum(len(data["texts"][b]) for j in jobs for b in j["benches"])
    print(f"{len(jobs)} jobs, {n} forward passes")


# ----------------------------------------------------------------------------- analysis (local)
def analyze(a):
    sys.path.insert(0, str(HERE))
    from gap_check import strat_auc
    meta = {j["name"]: j for j in json.loads((OUT / "meta.json").read_text())}
    res = {r["name"]: r for r in json.loads((OUT / (a.file or "results.json")).read_text())}
    mm = json.loads((HERE / "results" / "module_map.json").read_text())
    ctx = {}
    for c in ("safety", "bff"):
        items, _, y, g, strata = load(c)
        ctx[c] = (y, g, strata)
    rng = np.random.default_rng(0)

    def scores(c, r):
        y, g, strata = ctx[c]
        n = len(r["p"])
        y, g, strata = y[:n], g[:n], strata[:n]
        K = np.array(r["k"])
        m = np.ones(n, bool)
        return dict(knows=strat_auc(y, K[:, REF[c]], strata, m)[0], late=strat_auc(y, K[:, LATE[c]], strata, m)[0],
                    says=strat_auc(y, np.array(r["p"]), strata, m)[0],
                    curve=[round(strat_auc(y, K[:, L], strata, m)[0], 4) for L in range(1, 24)],
                    p_mean=float(np.mean(r["p"])))

    # paired bootstrap over questions for the change in "knows" vs base
    def boot_delta(c, r, rb, layer, n=300):
        y, g, strata = ctx[c]
        k1, k0 = np.array(r["k"])[:, layer], np.array(rb["k"])[:, layer]
        ug = np.unique(g)
        idx = {u: np.where(g == u)[0] for u in ug}
        ds = []
        for _ in range(n):
            ix = np.concatenate([idx[u] for u in rng.choice(ug, len(ug))])
            m = np.ones(len(ix), bool)
            ds.append(strat_auc(y[ix], k1[ix], strata[ix], m)[0] - strat_auc(y[ix], k0[ix], strata[ix], m)[0])
        return [round(float(np.percentile(ds, 2.5)), 4), round(float(np.percentile(ds, 97.5)), 4)]

    rows = {}
    for name, r in res.items():
        j = meta[name]
        row = dict(name=name, family=j["family"], mode=j["mode"], share=j.get("share"),
                   comps=[f"L{l + 1} {'h' + str(h + 1) if k == 'head' else 'MLP'}" for k, l, h in j["comps"]])
        for c in j["benches"]:
            row[c] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in scores(c, r[c]).items()}
        rows[name] = row
    for name, row in rows.items():
        for c in ("safety", "bff"):
            if c in row and name != "base":
                b = rows["base"][c]
                row[c].update(d_knows=round(row[c]["knows"] - b["knows"], 4),
                              d_late=round(row[c]["late"] - b["late"], 4),
                              d_says=round(row[c]["says"] - b["says"], 4))
                if row["family"] in ("group", "boost", "single") or (c == "bff" and row["family"] == "bff_mlp"):
                    row[c]["ci_knows"] = boot_delta(c, res[name][c], res["base"][c], REF[c])

    def compare(name, fam, c, key="d_knows"):
        R = np.array([rows[n][c][key] for n in rows if rows[n]["family"] == fam])
        v = rows[name][c][key]
        return dict(value=v, rand_mean=round(float(R.mean()), 4), rand_min=round(float(R.min()), 4),
                    rand_max=round(float(R.max()), 4), more_drop_than=int((v < R).sum()),
                    more_rise_than=int((v > R).sum()), n=len(R))
    tests = dict(
        right_safety=compare("S_right", "rand3", "safety"), right_safety_late=compare("S_right", "rand3", "safety", "d_late"),
        right_bff=compare("S_right", "rand3", "bff"),
        wrong_safety=compare("S_wrong", "rand2", "safety"), wrong_safety_late=compare("S_wrong", "rand2", "safety", "d_late"),
        wrong_bff=compare("S_wrong", "rand3", "bff"))
    bmlp = sorted([(rows[n]["bff"]["d_knows"], n) for n in rows if rows[n]["family"] == "bff_mlp"])
    tests["bff_mlp19_rank"] = [n for _, n in bmlp].index("bff_mlp_19") + 1
    out = dict(rows=rows, tests=tests, ref=REF, late=LATE,
               clean=dict(safety=mm["safety"]["knows_curve"][REF["safety"] - 1], bff=mm["bff"]["knows_curve"][REF["bff"] - 1]))
    (HERE / "results" / ("switch_off.json" if not a.file else "switch_off_smoke.json")).write_text(json.dumps(out, indent=1))
    for name in ["base", "S_right", "S_wrong", "S_right_boost", "S_wrong_boost"] + \
            [n for n in rows if rows[n]["family"] == "single"]:
        if name in rows:
            print(name, {c: {k: rows[name][c].get(k) for k in ("knows", "late", "says", "d_knows", "ci_knows")}
                         for c in ("safety", "bff") if c in rows[name]})
    for k, v in tests.items():
        print(k, v)
    print("bff mlp by d_knows:", [(n, d) for d, n in bmlp])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    an = sub.add_parser("analyze")
    an.add_argument("--file")
    a = ap.parse_args()
    {"build": build, "analyze": analyze}[a.cmd](a)
