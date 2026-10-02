"""
Deploy jeff (https://github.com/firelex/jeff) as a persistent Modal GPU web endpoint, base model only
(jeff-latest, v1.2) -- none of its 9 published adapters match our finance-correctness judging task.

jeff speaks the same POST /v1/systemone wire protocol as Jev (see experiments/common/backends.py's
HTTPSystemOne), so once deployed, point our EXISTING scripts at it directly:

  uv run python experiments/jev_bff/run_jev_bff.py --backend jeff --clm-url <printed-url>
  uv run python experiments/jev_router/run_jev_router.py --backend jeff --clm-url <printed-url>

Deploy (prints the URL):
  uv run modal deploy experiments/jeff_modal.py
Tear down when done (stops GPU billing):
  uv run modal app stop dynamic-llm-juries-jeff
"""
import modal

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .run_commands("git clone --depth 1 https://github.com/firelex/jeff /opt/jeff")
    .run_commands("pip install /opt/jeff --no-deps")
    .pip_install(
        "torch==2.14.0", "torchvision==0.29.0", "transformers==5.17.0", "pillow==12.3.0",
        "fastapi==0.141.1", "uvicorn==0.52.4", "safetensors==0.8.0", "numpy==2.5.3",
        "huggingface-hub==1.31.0", "flash-linear-attention==0.5.2", "kernels==0.16.1",
    )
    .run_commands(
        "hf download mstrasser/Jeff-Qwen3.5-0.8B --revision v1.2 --local-dir /opt/jeff-ckpt"
    )
)

app = modal.App("dynamic-llm-juries-jeff", image=image)


@app.function(gpu="T4", timeout=3600, min_containers=0, scaledown_window=600)
@modal.concurrent(max_inputs=16)
@modal.web_server(port=8765, startup_timeout=300)
def serve():
    import os
    import subprocess
    env = os.environ.copy()
    env.update(JEFF_CHECKPOINT="/opt/jeff-ckpt", PORT="8765", JEFF_HOST="0.0.0.0")
    subprocess.Popen(["jeff-serve"], env=env)
