#!/usr/bin/env python3
"""
Edit controls: was the Step 2 weight edit significant, or would a random edit of the same size do as well?

The edit adds  delta W_down[:, N] = alpha * s * u k^T  to one MLP's output weights: N neurons, a detector k (fit so
k . a ~ z, the layer-14 probe's "knows" score), and a push u (the direction that raises logit CORRECT - INCORRECT).
We rebuild it under the team's safety prompt and swap ONE ingredient at a time for a random version:

  real            256 neurons most correlated with z in layer 17, detector fit to z, push u_17
  rand_neurons    256 random neurons in layer 17, detector fit to the real z            (x19)
  shuffled        the whole recipe on labels shuffled within each request              (x19)
  rand_push       real neurons and detector, push in a random direction                (x19)
  rand_change     a random weight change on the real 256 columns                       (x19)
  layer_L         the real recipe in layer 9, 13, 16 or 20
  repro_generic   the original saved edit, scored under the original generic prompt (reproduction check)

Every edit is scaled to the same size: the mean norm of what it adds to the residual stream on training items equals
the real edit's (alpha = 0.2 as in Step 2). Fitting uses TRAIN items only (module_map's recorded activations);
scoring uses the 168 Safety TEST items (AUROC overall and same-source), the 74 BFF TEST items (finance prompt) and the
loss on 20 WikiText-2 passages. Edits run in parallel on Modal GPUs.

  modal run experiments/weight_space/edit_controls.py::dirs          # push directions under the safety prompt
  .venv/bin/python experiments/weight_space/edit_controls.py build   # fit all edits locally
  modal run experiments/weight_space/edit_controls.py::evaluate      # score all edits (add --limit 3 to smoke test)
  .venv/bin/python experiments/weight_space/edit_controls.py analyze
"""
import argparse, json, sys
from pathlib import Path

try:             # the Modal CLI's own Python has no numpy; remote functions import it themselves
    import numpy as np
except ImportError:
    np = None

try:
    import modal
except ImportError:
    modal = None

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "raw" / "edit_controls"
MM = HERE / "results" / "raw" / "module_map"
LAYERS = (9, 13, 16, 17, 20)          # hidden-state index L = output of block L-1, whose MLP we edit
REAL_LAYER, N_NEUR, ALPHA, NREP = 17, 256, 0.2, 19
POS_ID, NEG_ID = 25619, 17579          # " CORRECT" / " INCORRECT" first tokens


# ----------------------------------------------------------------------------- GPU side
def _load():
    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")
    model = AutoModelForImageTextToText.from_pretrained("Qwen/Qwen3.5-0.8B", dtype=torch.bfloat16).to("cuda").eval()
    return tok, model


def _enc(tok, text):
    p = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False, add_generation_prompt=True,
                                enable_thinking=False) + "VERDICT:"
    return tok(p, return_tensors="pt", truncation=True, max_length=8192).to("cuda")


def dirs_remote(texts: list) -> dict:
    """Mean normalized gradient of logit(COR) - logit(INC) w.r.t. the residual at each layer (verdict position)."""
    import numpy as np
    import torch
    tok, model = _load()
    acc = {L: torch.zeros(1024, device="cuda") for L in LAYERS}
    norms = {L: [] for L in LAYERS}
    for t in texts:
        o = model(**_enc(tok, t), output_hidden_states=True, logits_to_keep=1, use_cache=False)
        for L in LAYERS:
            o.hidden_states[L].retain_grad()
        (o.logits[0, -1, POS_ID] - o.logits[0, -1, NEG_ID]).float().backward()
        for L in LAYERS:
            g = o.hidden_states[L].grad[0, -1].float()
            acc[L] += g / g.norm()
            norms[L].append(o.hidden_states[L][0, -1].float().norm().item())
        model.zero_grad(set_to_none=True)
    return {L: dict(u=(acc[L] / acc[L].norm()).cpu().numpy().tolist(), s=float(np.median(norms[L]))) for L in LAYERS}


def eval_remote(jobs: list, data: dict) -> list:
    """For each job (an edit or None): verdict probabilities on Safety (job's prompt) and BFF test, WikiText loss."""
    import numpy as np
    import torch
    tok, model = _load()
    layers = model.model.language_model.layers

    def verdicts(texts):
        out = []
        for t in texts:
            with torch.no_grad():
                lg = model(**_enc(tok, t), logits_to_keep=1, use_cache=False).logits[0, -1].float()
            out.append(float(torch.sigmoid(lg[POS_ID] - lg[NEG_ID])))
        return out

    def wiki():
        ls = []
        for ids in data["wiki"]:
            x = torch.tensor([ids], device="cuda")
            with torch.no_grad():
                lg = model(input_ids=x, use_cache=False).logits[0, :-1].float()
            ls.append(float(torch.nn.functional.cross_entropy(lg, x[0, 1:])))
        return float(np.mean(ls))

    res = []
    for j in jobs:
        W = orig = cols = None
        if j["layer"]:
            W = layers[j["layer"] - 1].mlp.down_proj.weight
            cols = torch.as_tensor(j["cols"], device="cuda")
            orig = W[:, cols].clone()
            delta = torch.as_tensor(np.frombuffer(j["delta"], np.float32).reshape(1024, len(j["cols"])).copy(),
                                    device="cuda")
            with torch.no_grad():
                W[:, cols] = (orig.float() + delta).to(W.dtype)
        try:
            r = dict(name=j["name"], safety=verdicts(data["safety_" + j["prompt"]]), bff=verdicts(data["bff"]),
                     wiki=wiki())
        finally:
            if W is not None:
                with torch.no_grad():
                    W[:, cols] = orig
        res.append(r)
        print(j["name"], "done", flush=True)
    return res


def dirs_main():
    items = [json.loads(l) for l in open(MM / "safety" / "items.jsonl")]
    texts = [it["text"] for it in items if it["split"] == "train"][:64]
    d = dirs_remote.remote(texts)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "directions.json").write_text(json.dumps(d))
    print({L: round(v["s"], 2) for L, v in d.items()})


def evaluate_main(limit: int = 0, per: int = 9):
    import pickle
    jobs = pickle.loads((OUT / "jobs.pkl").read_bytes())
    data = pickle.loads((OUT / "data.pkl").read_bytes())
    if limit:
        jobs = jobs[:limit]
        data = dict(data, safety_safety=data["safety_safety"][:limit * 4], safety_generic=data["safety_generic"][:limit * 4],
                    bff=data["bff"][:limit * 2], wiki=data["wiki"][:2])
    chunks = [jobs[i:i + per] for i in range(0, len(jobs), per)]
    print(f"{len(jobs)} jobs in {len(chunks)} containers", flush=True)
    res = []
    for r in eval_remote.starmap([(c, data) for c in chunks]):
        res += r
    (OUT / ("smoke_results.json" if limit else "results.json")).write_text(json.dumps(res))
    print("saved", len(res))


if modal is not None:
    image = (modal.Image.debian_slim(python_version="3.12")
             .pip_install("torch==2.15.0", "transformers==5.22.2", "numpy==2.5.4")
             .env({"HF_HOME": "/root/.cache/huggingface"}))
    hf_cache = modal.Volume.from_name("dlj-hf-cache", create_if_missing=True)
    app = modal.App("weight-space-edit-controls", image=image)
    gpu = ["L4", "A10G", "L40S", "A100-40GB"]
    vols = {"/root/.cache/huggingface": hf_cache}
    dirs_remote = app.function(gpu=gpu, timeout=1800, volumes=vols)(dirs_remote)
    eval_remote = app.function(gpu=gpu, timeout=3600, volumes=vols)(eval_remote)
    dirs = app.local_entrypoint()(dirs_main)
    evaluate = app.local_entrypoint()(evaluate_main)


# ----------------------------------------------------------------------------- build edits (local)
def build(a):
    import pickle
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from transformers import AutoTokenizer
    sys.path.insert(0, str(HERE))
    import step2_edit
    items = [json.loads(l) for l in open(MM / "safety" / "items.jsonl")]
    Z = np.load(MM / "safety" / "acts.npz")
    HS, MLP = Z["hs"].astype(np.float32), Z["mlp"]
    y = np.array([it["gold"] for it in items])
    g = np.array([it["group"] for it in items])
    tr = np.array([it["split"] == "train" for it in items])
    D = {int(L): v for L, v in json.loads((OUT / "directions.json").read_text()).items()}
    rng = np.random.default_rng(0)

    def zscore(labels):
        sc = StandardScaler().fit(HS[tr, 14])
        lr = LogisticRegression(C=0.3, max_iter=3000).fit(sc.transform(HS[tr, 14]), labels[tr])
        d = lr.decision_function(sc.transform(HS[:, 14]))
        return (d - d[tr].mean()) / d[tr].std()

    def shuffled_labels():
        yy = y.copy()
        for k in np.unique(g):
            ix = np.where(g == k)[0]
            yy[ix] = rng.permutation(y[ix])
        return yy

    z = zscore(y)
    A = {L: MLP[:, L - 1].astype(np.float32) for L in LAYERS}

    def size(L, cols, delta):   # mean norm of what the edit adds to the residual on train items
        return float(np.linalg.norm(A[L][tr][:, cols] @ delta.T, axis=1).mean())

    def recipe(L, zz, cols=None):
        if cols is None:
            cols, k = step2_edit.fit_key(A[L], zz, N_NEUR, tr)
        else:
            cols = np.sort(cols)
            X = A[L][tr][:, cols]
            k = np.linalg.solve(X.T @ X + 1e-3 * np.trace(X.T @ X) / N_NEUR * np.eye(N_NEUR), X.T @ zz[tr])
        return cols, k

    def make(name, family, L, cols, k, u):
        return dict(name=name, family=family, layer=L, cols=[int(c) for c in cols],
                    delta=(ALPHA * D[L]["s"] * np.outer(u, k)).astype(np.float32))

    u17 = np.array(D[REAL_LAYER]["u"])
    cols, k = recipe(REAL_LAYER, z)
    real = make("real", "real", REAL_LAYER, cols, k, u17)
    T = size(REAL_LAYER, real["cols"], real["delta"])
    edits = [real]
    for i in range(NREP):
        c2, k2 = recipe(REAL_LAYER, z, cols=rng.choice(3584, N_NEUR, replace=False))
        edits.append(make(f"rand_neurons_{i}", "rand_neurons", REAL_LAYER, c2, k2, u17))
        c3, k3 = recipe(REAL_LAYER, zscore(shuffled_labels()))
        edits.append(make(f"shuffled_{i}", "shuffled", REAL_LAYER, c3, k3, u17))
        ur = rng.standard_normal(1024)
        edits.append(make(f"rand_push_{i}", "rand_push", REAL_LAYER, cols, k, ur / np.linalg.norm(ur)))
        edits.append(dict(name=f"rand_change_{i}", family="rand_change", layer=REAL_LAYER, cols=real["cols"],
                          delta=rng.standard_normal((1024, N_NEUR)).astype(np.float32)))
    for L in (9, 13, 16, 20):
        cL, kL = recipe(L, z)
        edits.append(make(f"layer_{L}", "layer", L, cL, kL, np.array(D[L]["u"])))
    for e in edits:   # same size for every edit
        e["delta"] = (e["delta"] * (T / size(e["layer"], e["cols"], e["delta"]))).astype(np.float32)
        e["size"] = size(e["layer"], e["cols"], e["delta"])
        e["prompt"] = "safety"

    from safetensors.numpy import load_file
    orig = load_file(str(HERE / "results" / "step2_edit_diff.safetensors"))
    edits.append(dict(name="repro_generic", family="repro", layer=17, cols=[int(c) for c in orig["columns"]],
                      delta=orig["delta"].astype(np.float32), prompt="generic", size=None))
    edits += [dict(name="base_safety", family="base", layer=0, cols=[], delta=np.zeros(0, np.float32), prompt="safety"),
              dict(name="base_generic", family="base", layer=0, cols=[], delta=np.zeros(0, np.float32), prompt="generic")]
    jobs = [dict(name=e["name"], layer=e["layer"], cols=e["cols"], delta=e["delta"].tobytes(), prompt=e["prompt"])
            for e in edits]
    meta = [dict(name=e["name"], family=e["family"], layer=e["layer"], size=e.get("size"),
                 overlap_real=len(set(e["cols"]) & set(real["cols"])) if e["layer"] == REAL_LAYER else None)
            for e in edits]

    gen = [json.loads(l) for l in open(HERE / "results" / "raw" / "prompt_ctrl" / "rb2_generic" / "items.jsonl")]
    bff = [json.loads(l) for l in open(MM / "bff" / "items.jsonl")]
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")
    from datasets import load_dataset
    text = "\n\n".join(t for t in load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1", split="test")["text"] if t.strip())
    ids = tok(text)["input_ids"]
    data = dict(safety_safety=[it["text"] for it in items if it["split"] == "test"],
                safety_generic=[it["text"] for it in gen if it["split"] == "test"],
                bff=[it["text"] for it in bff if it["split"] == "test"],
                wiki=[ids[c * 256:(c + 1) * 256] for c in range(20)])
    (OUT / "jobs.pkl").write_bytes(pickle.dumps(jobs))
    (OUT / "data.pkl").write_bytes(pickle.dumps(data))
    (OUT / "meta.json").write_text(json.dumps(dict(edits=meta, target_size=T, real_cols=real["cols"])))
    print(f"{len(jobs)} jobs; target size {T:.3f}; test sizes", {k: len(v) for k, v in data.items()})


# ----------------------------------------------------------------------------- analysis (local)
def analyze(a):
    sys.path.insert(0, str(HERE))
    from gap_check import auc, strat_auc
    meta = {m["name"]: m for m in json.loads((OUT / "meta.json").read_text())["edits"]}
    res = {r["name"]: r for r in json.loads((OUT / "results.json").read_text())}
    S = [json.loads(l) for l in open(MM / "safety" / "items.jsonl")]
    S = [it for it in S if it["split"] == "test"]
    B = [json.loads(l) for l in open(MM / "bff" / "items.jsonl")]
    B = [it for it in B if it["split"] == "test"]
    ys, yb = np.array([it["gold"] for it in S]), np.array([it["gold"] for it in B])
    strata = np.array([f"{it['resp_model']}|{it['refusal']}" for it in S])
    m = np.ones(len(ys), bool)
    rows = {}
    for name, r in res.items():
        p = np.array(r["safety"])
        rows[name] = dict(meta[name], safety=round(auc(ys, p), 4), safety_ss=round(strat_auc(ys, p, strata, m)[0], 4),
                          says_correct=round(float((p > .5).mean()), 3), bff=round(auc(yb, np.array(r["bff"])), 4),
                          wiki=round(r["wiki"], 4))
    base = rows["base_safety"]
    for r in rows.values():
        b = rows["base_generic"] if r["name"] in ("repro_generic", "base_generic") else base
        r.update(gain=round(r["safety"] - b["safety"], 4), gain_ss=round(r["safety_ss"] - b["safety_ss"], 4),
                 bff_drop=round(b["bff"] - r["bff"], 4), wiki_up=round(r["wiki"] - b["wiki"], 4))
    real = rows["real"]
    fams = {}
    for f in ("rand_neurons", "shuffled", "rand_push", "rand_change"):
        R = [r for r in rows.values() if r["family"] == f]
        g = np.array([r["safety"] for r in R])
        fams[f] = dict(n=len(R), safety_mean=round(float(g.mean()), 4), safety_min=round(float(g.min()), 4),
                       safety_max=round(float(g.max()), 4), beats=int((real["safety"] > g).sum()),
                       z=round(float((real["safety"] - g.mean()) / (g.std() + 1e-9)), 2),
                       bff_drop_mean=round(float(np.mean([r["bff_drop"] for r in R])), 4),
                       wiki_up_mean=round(float(np.mean([r["wiki_up"] for r in R])), 4))
    out = dict(rows=rows, families=fams)
    (HERE / "results" / "edit_controls.json").write_text(json.dumps(out, indent=1))
    show = ["base_safety", "real", "layer_9", "layer_13", "layer_16", "layer_20", "base_generic", "repro_generic"]
    for n in show:
        r = rows[n]
        print(f"{n:15s} safety {r['safety']:.3f} ss {r['safety_ss']:.3f} saysC {r['says_correct']:.2f} "
              f"bff {r['bff']:.3f} wiki {r['wiki']:.3f}")
    for f, v in fams.items():
        print(f, v)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("analyze")
    a = ap.parse_args()
    {"build": build, "analyze": analyze}[a.cmd](a)
