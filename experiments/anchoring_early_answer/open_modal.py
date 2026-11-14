"""OLMo-3 training-stage study on Modal: one H100 per checkpoint, all in parallel.

For each checkpoint: gen_vllm.py (its own answers + judging transcripts, 64K budget), then probe_steer.py --phase
readout (verdict at every checkpoint + hidden states at A / E / C). The base model only gets the position-A
readout and capture (it cannot follow the judge format). Outputs: /vol/anchoring_open/<key>/.

  .venv/bin/modal run --detach experiments/anchoring_early_answer/open_modal.py --keys olmo3-7b-instruct-sft --limit 3
  .venv/bin/modal run --detach experiments/anchoring_early_answer/open_modal.py              # all stages
  .venv/bin/modal run experiments/anchoring_early_answer/open_modal.py --pull-only [--hidden]
"""
import json
import pathlib
import subprocess
import sys
import threading

import modal

_here = pathlib.Path(__file__).resolve()
REPO = _here.parents[2] if len(_here.parents) > 2 else pathlib.Path("/root/repo")
HERE = "/root/repo/experiments/anchoring_early_answer"

# key -> (HF id, kind). Training order: base -> SFT -> DPO -> RL (the released final model).
STAGES = {
    "olmo3-7b-base": ("allenai/Olmo-3-1025-7B", "plain"),
    "olmo3-7b-instruct-sft": ("allenai/Olmo-3-7B-Instruct-SFT", "instruct"),
    "olmo3-7b-instruct-dpo": ("allenai/Olmo-3-7B-Instruct-DPO", "instruct"),
    "olmo3-7b-instruct": ("allenai/Olmo-3-7B-Instruct", "instruct"),
    "olmo3-7b-think-sft": ("allenai/Olmo-3-7B-Think-SFT", "think"),
    "olmo3-7b-think-dpo": ("allenai/Olmo-3-7B-Think-DPO", "think"),
    "olmo3-7b-think": ("allenai/Olmo-3-7B-Think", "think"),
}

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("vllm==0.11.0", "transformers==4.57.1", "accelerate>=0.34", "numpy", "huggingface_hub")
    .add_local_dir(REPO / "experiments" / "llama_bbeh", "/root/repo/experiments/llama_bbeh",
                   ignore=["**/*results*/**", "**/__pycache__/**"])
    .add_local_dir(REPO / "experiments" / "anchoring_early_answer", HERE,
                   ignore=["out/**", "out_pilot/**", "out_probe/**", "out_llama/**", "out_open/**", "**/__pycache__/**"])
)
app = modal.App("dynamic-llm-juries-olmo-stages", image=image)
vol = modal.Volume.from_name("dynamic-llm-juries-results", create_if_missing=True)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=24 * 3600, volumes={"/vol": vol, "/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def stage(key: str, limit: int = 0, shard: int = 0, nshards: int = 1, gen_only: bool = False,
          readout_only: bool = False) -> str:
    """One checkpoint. Thinking stages are slow (long outputs): generate in nshards containers (gen_only), then run
    readout_only once all shards are saved; the shard files are merged into generations.jsonl first."""
    model, kind = STAGES[key]
    out = f"/vol/anchoring_open/{key}" + ("_pilot" if limit else "")
    stop = threading.Event()

    def committer():
        while not stop.wait(60):
            vol.commit()

    threading.Thread(target=committer, daemon=True).start()
    lim = ["--limit", str(limit)] if limit else []
    try:
        if kind != "plain" and not readout_only:
            subprocess.run([sys.executable, f"{HERE}/gen_vllm.py", "--model", model, "--out", out, "--shard", str(shard),
                            "--nshards", str(nshards), "--chunk", "64" if kind == "think" else "512"] + lim,
                           check=True, cwd=HERE)
            hf_cache.commit()
        if gen_only:
            return f"{key} shard {shard}/{nshards}: generated"
        shards = sorted(pathlib.Path(out).glob("generations_s*.jsonl"))
        if shards:  # merge shard files (and any earlier single file) into generations.jsonl, keyed, no duplicates
            rows = {}
            for f in sorted(pathlib.Path(out).glob("generations*.jsonl")):
                for line in open(f):
                    rows.setdefault(json.loads(line)["key"], line)
            pathlib.Path(out, "generations.jsonl").write_text("".join(rows.values()))
        cmd = [sys.executable, f"{HERE}/probe_steer.py", "--phase", "readout", "--model", model, "--judge", key,
               "--prompts-from", "qwen3.5-4b", "--out", out] + lim
        cmd += ["--plain"] if kind == "plain" else ["--gen", f"{out}/generations.jsonl"]
        cmd += ["--think"] if kind == "think" else []
        subprocess.run(cmd, check=True, cwd=HERE)
    finally:
        stop.set()
        vol.commit()
        hf_cache.commit()
    return f"{key}: done"


@app.function(timeout=24 * 3600)
def orchestrate(think_keys: list, other_keys: list, shards: int = 4) -> str:
    """Runs entirely on Modal (deploy the app, then .spawn() this), so the laptop's connection does not matter.
    Thinking stages: `shards` generation containers each, then one readout container. Other stages: the normal
    stage() (generation resumes from what is saved, e.g. only BFF is new; then a full readout)."""
    others = [stage.spawn(k) for k in other_keys]
    gen = list(stage.starmap([(k, 0, s, shards, True) for k in think_keys for s in range(shards)],
                             return_exceptions=True))
    print(gen, flush=True)
    ro = list(stage.map(think_keys, kwargs={"readout_only": True}, return_exceptions=True))
    print(ro, flush=True)
    done = []
    for c in others:
        try:
            done.append(c.get())
        except Exception as e:  # noqa: BLE001
            done.append(f"failed: {e}")
    return "\n".join(map(str, gen + ro + done))


@app.function(volumes={"/vol": vol}, timeout=3600)
def pull(key: str, pilot: bool, hidden: bool) -> dict:
    vol.reload()
    d = pathlib.Path(f"/vol/anchoring_open/{key}" + ("_pilot" if pilot else ""))
    if not d.exists():
        return {}
    return {p.name: p.read_bytes() for p in d.iterdir() if p.is_file() and (hidden or p.suffix != ".npy")}


@app.local_entrypoint()
def main(keys: str = "", limit: int = 0, pull_only: bool = False, hidden: bool = False, shards: int = 1):
    """--shards N: thinking stages generate in N containers each, then one readout container per stage."""
    ks = [k for k in keys.split(",") if k] or list(STAGES)
    if not pull_only and shards > 1:
        args = [(k, s) for k in ks for s in range(shards)]
        for r in stage.starmap([(k, limit, s, shards, True) for k, s in args], return_exceptions=True):
            print(r, flush=True)
        for r in stage.map(ks, kwargs={"limit": limit, "readout_only": True}, return_exceptions=True):
            print(r, flush=True)
    elif not pull_only:
        for r in stage.map(ks, kwargs={"limit": limit}, return_exceptions=True):
            print(r, flush=True)
    for k in ks:
        dest = _here.parent / "out_open" / (k + ("_pilot" if limit else ""))
        dest.mkdir(parents=True, exist_ok=True)
        files = pull.remote(k, bool(limit), hidden or bool(limit))
        for name, data in files.items():
            (dest / name).write_bytes(data)
        print(f"pulled {k}: {sorted(files)}", flush=True)
