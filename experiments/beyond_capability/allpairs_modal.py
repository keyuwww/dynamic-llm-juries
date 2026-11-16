"""Modal H100: every (judge, benchmark) pair through azure/pair_pipeline.py (gap check -> push test -> layer rule ->
stretch x11 at the chosen layer), plus the judge's own solve labels where they are missing. Rule: out_allpairs/RULE.md.
One container per pair, all in parallel. Outputs: volume dynamic-llm-juries-results:/beyond_capability_allpairs/<pair>/
-> out_allpairs/<pair>/ (choice_*.json, final_*.jsonl, meta_*.jsonl, esolves_*.jsonl).

  .venv/bin/modal run experiments/beyond_capability/allpairs_modal.py --phase smoke
  .venv/bin/modal run --detach experiments/beyond_capability/allpairs_modal.py --phase run
  .venv/bin/modal run experiments/beyond_capability/allpairs_modal.py --phase pull
"""
import json
import pathlib
import subprocess
import sys

import modal

_here = pathlib.Path(__file__).resolve()
HERE = "/root/bc"
MODELS = {
    "llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct",
    "llama3.2-3b": "meta-llama/Llama-3.2-3B-Instruct",
    "qwen3.5-4b": "Qwen/Qwen3.5-4B",
    "phi4-mini": "microsoft/Phi-4-mini-instruct",
    "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
    "granite3.3-8b": "ibm-granite/granite-3.3-8b-instruct",
    "llama3.2-1b": "meta-llama/Llama-3.2-1B-Instruct",  # fresh judges for the score-based rule (RULE_v2.md)
    "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
}
FRESH = [(j, b) for j in ("llama3.2-1b", "qwen2.5-7b") for b in ("mmlu", "math", "bbeh")]
NO_CACHE = {"qwen3.5-4b"}  # hybrid attention: the recurrent state can't be cropped
BENCH = {"mmlu": ("mmlu_full_items.jsonl.gz", "solveq_mmlu.jsonl", 4096),
         "math": ("math_full_items.jsonl.gz", "solveq_math.jsonl", 8192),
         "bbeh": ("bbeh_items.jsonl.gz", "solveq_bbeh.jsonl", 8192)}
# (judge, bench, needs solve labels). Not here: Llama-3.1-8B MATH and Llama-3.2-3B MMLU (layer sweeps done), and pairs
# whose gap was already measured <= 5 (Qwen3.5-9B everywhere, Qwen3.5-4B MMLU).
PAIRS = [
    ("llama3.1-8b", "mmlu", False), ("phi4-mini", "mmlu", False), ("mistral-7b", "mmlu", True), ("granite3.3-8b", "mmlu", True),
    ("llama3.1-8b", "bbeh", False), ("llama3.2-3b", "bbeh", True), ("qwen3.5-4b", "bbeh", False), ("phi4-mini", "bbeh", True),
    ("mistral-7b", "bbeh", True), ("granite3.3-8b", "bbeh", True),
    ("llama3.2-3b", "math", True), ("qwen3.5-4b", "math", False), ("phi4-mini", "math", True), ("mistral-7b", "math", True),
    ("granite3.3-8b", "math", True),
]

def make_image(transformers_spec, extra=()):
    img = (modal.Image.debian_slim(python_version="3.11")
           .pip_install("torch>=2.5", transformers_spec, "accelerate>=0.34", "numpy", "huggingface_hub", "sentencepiece", "protobuf", *extra)
           .add_local_file(_here.parent / "azure" / "dir_capture.py", f"{HERE}/dir_capture.py")
           .add_local_file(_here.parent / "azure" / "pair_pipeline.py", f"{HERE}/pair_pipeline.py"))
    for b in BENCH.values():
        for f in b[:2]:
            img = img.add_local_file(_here.parent / "inputs" / f, f"{HERE}/inputs/{f}")
    for f in ("sm_mmlu_items.jsonl.gz", "sm_math_items.jsonl.gz", "sm_bbeh_items.jsonl.gz"):  # same-model test items
        if (_here.parent / "inputs" / f).exists():
            img = img.add_local_file(_here.parent / "inputs" / f, f"{HERE}/inputs/{f}")
    return img


# v4 for the KV-cache shortcut (Cache.crop as used here; checked in layer_sweep_modal.py --phase smoke);
# v5 for Qwen3.5 (hybrid attention; re-runs the whole prompt per edit, so no crop)
image = make_image("transformers>=4.57,<5")
image_v5 = make_image("transformers>=5", ("flash-linear-attention",))
app = modal.App("dlj-beyond-capability-allpairs", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
ROOT = "/vol/beyond_capability_allpairs"


@app.function(volumes={"/root/.cache/huggingface": hf_cache}, secrets=[modal.Secret.from_name("huggingface")],
              timeout=3600)
def download() -> str:
    from huggingface_hub import snapshot_download
    for m in MODELS.values():
        snapshot_download(m, allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.jinja", "*.py", "tokenizer*"])
        hf_cache.commit()
    return "downloaded"


def sh(args):
    import threading
    stop = threading.Event()

    def committer():
        while not stop.wait(60):
            vol.commit()
    threading.Thread(target=committer, daemon=True).start()
    try:
        subprocess.run([sys.executable, f"{HERE}/pair_pipeline.py", *args], check=True, cwd=HERE)
    finally:
        stop.set()
        vol.commit()


GPU = dict(gpu="H100", timeout=6 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
           secrets=[modal.Secret.from_name("huggingface")])


@app.function(**GPU)
def pair(judge: str, bench: str, need_solve: bool, limit: int = 0, rule: str = "v1") -> str:
    return _pair(judge, bench, need_solve, limit, rule)


@app.function(image=image_v5, **GPU)
def pair_v5(judge: str, bench: str, need_solve: bool, limit: int = 0) -> str:
    return _pair(judge, bench, need_solve, limit)


def _pair(judge, bench, need_solve, limit=0, rule="v1"):
    vol.reload()
    items, qfile, max_new = BENCH[bench]
    out = f"{ROOT}/{judge}_{bench}" + ("_smoke" if limit else "")
    common = ["--model", MODELS[judge], "--out", out, "--tag", bench] + (["--no-cache"] if judge in NO_CACHE else [])
    sh(["--phase", "pair", "--items", f"{HERE}/inputs/{items}", "--rule", rule, *common]
       + (["--limit", str(limit), "--force"] if limit else []))
    ch = json.load(open(f"{out}/choice_{bench}.json"))
    if need_solve and "stopped" not in ch:
        sh(["--phase", "solve", "--qfile", f"{HERE}/inputs/{qfile}", "--max-new", str(max_new), "--batch", "64",
            *common[:4], "--tag", f"{bench}_{judge}"] if not limit else
           ["--phase", "solve", "--qfile", f"{HERE}/inputs/{qfile}", "--max-new", "512", "--batch", "8", "--limit", "16",
            *common[:4], "--tag", f"{bench}_{judge}"])
    return f"{judge} {bench}: gap {ch['gap']:+.1f}, " + (ch.get("stopped") or f"layer {ch['chosen_layer']} ({ch['rule']})")


def _diagnose(judge, bench):
    vol.reload()
    items = BENCH[bench][0]
    out = f"{ROOT}/{judge}_{bench}"
    common = ["--model", MODELS[judge], "--out", out, "--tag", bench, "--items", f"{HERE}/inputs/{items}"] + \
        (["--no-cache"] if judge in NO_CACHE else [])
    if not pathlib.Path(f"{out}/captured_{bench}").exists():
        sh(["--phase", "pair", "--capture-only", *common])
    sh(["--phase", "diagnose", *common])
    return f"diagnosed {judge} {bench}"


@app.function(**GPU)
def diagnose(judge: str, bench: str) -> str:
    return _diagnose(judge, bench)


@app.function(image=image_v5, **GPU)
def diagnose_v5(judge: str, bench: str) -> str:
    return _diagnose(judge, bench)


N_LAYERS = {"llama3.2-1b": 16, "qwen2.5-7b": 28, "llama3.1-8b": 32, "llama3.2-3b": 28, "qwen3.5-4b": 32, "phi4-mini": 32, "mistral-7b": 32, "granite3.3-8b": 40}


def _extra(judge, bench, layer):
    """judge the same-model test items (inputs/sm_<bench>_items.jsonl.gz) at a fixed layer with the pair's directions."""
    vol.reload()
    out = f"{ROOT}/{judge}_{bench}"
    sh(["--phase", "extra", "--model", MODELS[judge], "--out", out, "--tag", bench, "--layer", str(layer),
        "--n-layers", str(N_LAYERS[judge]), "--extra-items", f"{HERE}/inputs/sm_{bench}_items.jsonl.gz"]
       + (["--no-cache"] if judge in NO_CACHE else []))
    return f"extra done: {judge} {bench} layer {layer}"


@app.function(**GPU)
def extra(judge: str, bench: str, layer: int) -> str:
    return _extra(judge, bench, layer)


@app.function(image=image_v5, **GPU)
def extra_v5(judge: str, bench: str, layer: int) -> str:
    return _extra(judge, bench, layer)


def _sweep(judge, bench):
    vol.reload()
    out = f"{ROOT}/{judge}_{bench}"
    sh(["--phase", "sweep", "--model", MODELS[judge], "--out", out, "--tag", bench, "--items",
        f"{HERE}/inputs/{BENCH[bench][0]}"] + (["--no-cache"] if judge in NO_CACHE else []))
    return f"swept {judge} {bench}"


@app.function(**GPU)
def sweep_pair(judge: str, bench: str) -> str:
    return _sweep(judge, bench)


@app.function(image=image_v5, **GPU)
def sweep_pair_v5(judge: str, bench: str) -> str:
    return _sweep(judge, bench)


@app.function(volumes={"/vol": vol}, timeout=3600, cpu=8, memory=32768)
def knows_splits(judge: str, bench: str, layer: int, n: int = 20) -> dict:
    """KNOWS at one layer over n random half-splits of the questions (how noisy the gap estimate is)."""
    import numpy as np
    vol.reload()
    d = pathlib.Path(f"{ROOT}/{judge}_{bench}")
    H = np.load(d / f"hidden_{bench}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(d / f"meta_{bench}.jsonl")]
    nl = N_LAYERS[judge]
    kept = sorted(set(range(0, nl + 1, 2)) | {nl})
    X = np.asarray(H[:, kept.index(layer)], np.float32)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    Xc = X.copy()
    for g in uq:
        Xc[q == g] -= X[q == g].mean(0)

    def auc(s):
        num = den = 0.0
        for g in uq:
            k = q == g
            a, b = s[k & (y == 1)], s[k & (y == 0)]
            if len(a) and len(b):
                num += (a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()
                den += len(a) * len(b)
        return num / den
    out = []
    for seed in range(n):
        h1q = set(np.random.default_rng(seed).permutation(uq)[: len(uq) // 2])
        h1 = np.array([x in h1q for x in q])
        s = np.zeros(len(y))
        for mask in (h1, ~h1):
            v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
            s[~mask] = X[~mask] @ (v / (np.linalg.norm(v) + 1e-9))
        out.append(auc(s))
    says = auc(np.array([m["margin"] for m in meta]))
    return dict(judge=judge, bench=bench, layer=layer, knows_mean=float(np.mean(out)), knows_sd=float(np.std(out)),
                knows_seed0=float(out[0]), says=float(says))


@app.function(volumes={"/vol": vol}, timeout=1800)
def pull() -> dict:
    vol.reload()
    root = pathlib.Path(ROOT)
    keep = ("choice_", "final_", "meta_", "diag_", "extra_", "sweep_")  # solve files are fetched by solve_vllm_modal.py
    return {f"{p.parent.name}/{p.name}": p.read_bytes() for p in root.glob("*/*") if p.name.startswith(keep)} \
        if root.exists() else {}


@app.local_entrypoint()
def main(phase: str = "run", pairs: str = ""):
    if phase == "smoke":
        print(download.remote())
        calls = [pair_v5.spawn("qwen3.5-4b", "mmlu", True, 120), pair.spawn("mistral-7b", "bbeh", True, 120)]
        for c in calls:
            print(c.get())
    if phase == "fresh":  # RULE_v2.md: new judges, score-based layer rule, no in-container solving
        print(download.remote())
        calls = [pair.spawn(j, b, False, 0, "v2") for j, b in FRESH]
        for (j, b), c in zip(FRESH, calls):
            try:
                print(c.get(), flush=True)
            except Exception as e:
                print(f"{j} {b}: FAILED {type(e).__name__}: {str(e)[:300]}", flush=True)
    if phase == "run":
        print(download.remote())
        calls = [(pair_v5 if j in NO_CACHE else pair).spawn(j, b, ns) for j, b, ns in PAIRS]
        for (j, b, _), c in zip(PAIRS, calls):
            try:
                print(c.get(), flush=True)
            except Exception as e:  # one failing pair must not stop the others
                print(f"{j} {b}: FAILED {type(e).__name__}: {str(e)[:300]}", flush=True)
    if phase == "diagnose":  # pairs given as judge:bench,judge:bench
        todo = [tuple(x.split(":")) for x in pairs.split(",")]
        calls = [(diagnose_v5 if j in NO_CACHE else diagnose).spawn(j, b) for j, b in todo]
        for (j, b), c in zip(todo, calls):
            try:
                print(c.get(), flush=True)
            except Exception as e:
                print(f"{j} {b}: FAILED {type(e).__name__}: {str(e)[:300]}", flush=True)
    if phase == "splits":  # judge:bench:layer,...
        todo = [x.split(":") for x in pairs.split(",")]
        res = list(knows_splits.starmap([(j, b, int(L)) for j, b, L in todo]))
        (_here.parent / "out_allpairs" / "knows_splits.json").write_text(json.dumps(res, indent=1))
        for r in res:
            print(f"{r['judge']:14s} {r['bench']} L{r['layer']}: knows seed0 {r['knows_seed0']:.3f}, 20-split mean "
                  f"{r['knows_mean']:.3f} ± {r['knows_sd']:.3f}; says {r['says']:.3f}; gap (mean) {100 * (r['knows_mean'] - r['says']):+.1f}")
        return
    if phase == "sweep":  # pairs given as judge:bench,...
        todo = [tuple(x.split(":")) for x in pairs.split(",")]
        calls = [(sweep_pair_v5 if j in NO_CACHE else sweep_pair).spawn(j, b) for j, b in todo]
        for c in calls:
            try:
                print(c.get(), flush=True)
            except Exception as e:
                print(f"FAILED {type(e).__name__}: {str(e)[:300]}", flush=True)
    if phase == "extra":  # pairs given as judge:bench:layer,...
        todo = [x.split(":") for x in pairs.split(",")]
        calls = [(extra_v5 if j in NO_CACHE else extra).spawn(j, b, int(L)) for j, b, L in todo]
        for c in calls:
            try:
                print(c.get(), flush=True)
            except Exception as e:
                print(f"FAILED {type(e).__name__}: {str(e)[:300]}", flush=True)
    files = pull.remote()
    dest = _here.parent / "out_allpairs"
    for name, data in files.items():
        p = dest / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    print(f"pulled {len(files)} files -> {dest}")
