"""Copy the OLMo-3 Think checkpoints from the Modal HF cache into C3 storage (C3 jobs have no internet).

Runs on a cheap Modal CPU container: dereferences each HF snapshot into a plain folder and `c3 data cp`s it to
/datasets/olmo3-think/<name>/. The C3 API key is read from a local file and passed as an ephemeral secret.

  C3_KEY_FILE=... .venv/bin/modal run experiments/anchoring_early_answer/c3_upload_modal.py
"""
import os
import pathlib
import subprocess

import modal

MODELS = ["Olmo-3-7B-Think-SFT", "Olmo-3-7B-Think-DPO", "Olmo-3-7B-Think"]
image = (modal.Image.debian_slim(python_version="3.11").apt_install("curl", "ca-certificates")
         .run_commands("curl -fsSL https://cthree.cloud/releases/latest/c3-linux-amd64 -o /usr/local/bin/c3",
                       "chmod +x /usr/local/bin/c3"))
app = modal.App("dlj-c3-upload", image=image)
hf_cache = modal.Volume.from_name("hf-cache")


def _secret():
    f = os.environ.get("C3_KEY_FILE")
    return modal.Secret.from_dict({"C3_API_KEY": pathlib.Path(f).read_text().strip()} if f else {})


@app.function(volumes={"/hf": hf_cache}, secrets=[_secret()], timeout=6 * 3600, cpu=8, memory=16384)
def upload(name: str, resource: str = "") -> str:
    snaps = sorted(pathlib.Path(f"/hf/hub/models--allenai--{name}/snapshots").iterdir())
    src = snaps[-1]
    dst = pathlib.Path(f"/tmp/{name}")
    if not dst.exists():
        subprocess.run(["cp", "-rL", f"{src}/.", str(dst)], check=True)  # resolve HF blob symlinks into real files
    files = sorted(p.name for p in dst.iterdir())
    env = dict(os.environ, C3_CLI_MULTIPART_CONCURRENCY="16")
    print(f"{name}: {files}", flush=True)
    if resource:  # persistent data resource (the JuiceFS path; dataset mounts are refused at submit)
        r = subprocess.run(["c3", "data", "resource", "upload", resource, str(dst), "0"], env=env, capture_output=True,
                           text=True)
        return f"{name}: rc={r.returncode} {r.stdout[-800:]} {r.stderr[-800:]}"
    r = subprocess.run(["c3", "data", "cp", f"{dst}/", f"/datasets/{name.lower()}/"], env=env)  # output streamed
    return f"{name}: rc={r.returncode}"


@app.local_entrypoint()
def main(resources: str = "", only: str = ""):
    """--resources sft_id,dpo_id,final_id: upload into C3 data resources (same order as MODELS), one at a time
    (parallel resource uploads get HTTP 409). --only Name1,Name2: just these models."""
    res = resources.split(",") if resources else [""] * len(MODELS)
    for m, r in zip(MODELS, res):
        if only and m not in only.split(","):
            continue
        try:
            print(upload.remote(m, r), flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{m}: failed {e}", flush=True)
