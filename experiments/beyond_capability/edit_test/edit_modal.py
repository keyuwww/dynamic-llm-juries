"""Score the controlled-edit pairs with frozen primary-evaluation readouts (PROTOCOL.md). Modal H100, one container per
judge. For a problem in outer half h the readouts are those of the fold whose test half is h: the direction fitted on
the other half (question-centred class means, as azure/outer_pipeline.py), its readout layer, and the stretch at its
stretch layer (x11, centring constant and scale from the training projections).

  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/edit_test/edit_modal.py --pairs test
-> edit_test/scores_<pairs>.json
"""
import json
import pathlib

import modal

HERE = pathlib.Path(__file__).resolve().parent
BC = HERE.parent
CODE = "/root/bc"
MODELS = {"llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct", "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
          "phi4-mini": "microsoft/Phi-4-mini-instruct", "granite3.3-8b": "ibm-granite/granite-3.3-8b-instruct"}
image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install("torch>=2.5", "transformers>=4.57,<5", "accelerate>=0.34", "numpy", "huggingface_hub", "sentencepiece",
                      "protobuf")
         .add_local_file(BC / "azure" / "dir_capture.py", f"{CODE}/dir_capture.py")
         .add_local_file(BC / "azure" / "pair_pipeline.py", f"{CODE}/pair_pipeline.py"))
app = modal.App("bc-edit-test", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results")
hf_cache = modal.Volume.from_name("hf-cache")


@app.function(gpu="H100", timeout=3 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")], memory=65536)
def score(judge: str, folds: dict, items: list) -> dict:
    import sys
    import numpy as np
    sys.path.insert(0, CODE)
    from dir_capture import build_ids
    from pair_pipeline import Judge
    d = pathlib.Path(f"/vol/beyond_capability_allpairs/{judge}_math")
    H = np.load(d / "hidden_math.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / "meta_math.jsonl")]
    J = Judge(MODELS[judge], use_cache=True)
    n = len(J.layers)
    kept = sorted(set(range(0, n + 1, 2)) | {n})
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    rd = {}
    for fold, te in (("h1", h1), ("h2", ~h1)):
        tr = ~te
        f = folds[fold]
        for role, L in (("direct", f["direct_layer"]), ("stretch", f["stretch_layer"])):
            X = np.asarray(H[:, kept.index(L)], np.float32)
            Xc = X.copy()
            for g in set(q):
                k = q == g
                Xc[k] -= X[k].mean(0)
            v = Xc[tr][y[tr] == 1].mean(0) - Xc[tr][y[tr] == 0].mean(0)
            v = v / (np.linalg.norm(v) + 1e-9)
            p = X[tr] @ v
            rd[(fold, role)] = (L, v, float(p.mean()), float(p.std()))
    import torch
    out = []
    for it in items:
        fold = "h1" if it["qid"] in h1q else "h2"
        ids = build_ids(J.tok, dict(messages=it["messages"], suffix="VERDICT:"))
        cache = J.prepare(ids)
        m0, hs = J.read(ids, cache, None, hidden=True)
        Ld, vd, _, _ = rd[(fold, "direct")]
        proj = float(hs[Ld][0, -1].float().cpu().numpy() @ vd)
        Ls, vs, mu, sd = rd[(fold, "stretch")]
        ed = dict(L=Ls, kind="amplify", s=10.0, v=torch.tensor(vs, dtype=torch.float32, device="cuda"), mu=mu, sd=sd)
        ms, _ = J.read(ids, cache, ed)
        del cache
        out.append(dict(aid=it["aid"], qid=it["qid"], kind=it["kind"], fold=fold, verdict=m0, direct=proj, stretch=ms,
                        rule=ms if folds[fold]["eligible"] else m0))
    return dict(judge=judge, rows=out)


@app.local_entrypoint()
def main(pairs: str = "test", limit: int = 0, judges: str = ""):
    import gzip
    src = {}
    for l in gzip.open(BC / "inputs" / "math_full_items.jsonl.gz", "rt"):
        r = json.loads(l)
        src[r["aid"]] = r
    P = [json.loads(l) for l in open(HERE / f"pairs_{pairs}.jsonl")][: limit or None]
    items = []
    for p in P:
        r = src[p["aid"]]
        content = r["messages"][-1]["content"]
        assert content.count(p["original"]) == 1, p["aid"]
        msg_e = [dict(m) for m in r["messages"]]
        msg_e[-1]["content"] = content.replace(p["original"], p["edited"])
        items.append(dict(aid=p["aid"], qid=p["qid"], kind="original", messages=r["messages"]))
        items.append(dict(aid=p["aid"], qid=p["qid"], kind="edited", messages=msg_e))
    args = []
    for j in (judges.split(",") if judges else MODELS):
        info = json.load(open(BC / "out_outer" / f"{j}_math" / "outer_math.json"))
        folds = {k: {x: f[x] for x in ("direct_layer", "stretch_layer", "eligible")} for k, f in info["folds"].items()}
        args.append((j, folds, items))
    res = {}
    for r in score.starmap(args, return_exceptions=True):
        if isinstance(r, Exception):
            print("FAILED", str(r)[:500])
            continue
        res[r["judge"]] = r["rows"]
        print(r["judge"], len(r["rows"]), flush=True)
    f = HERE / f"scores_{pairs}{'_smoke' if limit else ''}.json"
    old = json.load(open(f)) if f.exists() else {}
    json.dump(old | res, open(f, "w"))
