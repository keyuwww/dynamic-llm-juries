"""
Deploy Laya (https://github.com/NandhaKishorM/laya) as a persistent Modal GPU web endpoint.

Laya speaks the same POST /v1/systemone wire protocol as Jev (see experiments/common/backends.py's
HTTPSystemOne), so once this is deployed, point our EXISTING scripts at it directly -- no new client
code needed:

  uv run python experiments/jev_bff/run_jev_bff.py --backend laya --clm-url <printed-url>
  uv run python experiments/jev_router/run_jev_router.py --backend laya --clm-url <printed-url>

Deploy (prints the URL):
  uv run modal deploy experiments/laya_modal.py
Tear down when done (stops GPU billing):
  uv run modal app stop dynamic-llm-juries-laya
"""
import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("laya[serve]")
)

app = modal.App("dynamic-llm-juries-laya", image=image)


@app.function(gpu="T4", timeout=3600, min_containers=0, scaledown_window=600)
@modal.concurrent(max_inputs=16)
@modal.web_server(port=8000, startup_timeout=300)
def serve():
    import os
    import subprocess
    env = os.environ.copy()
    env.update(LAYA_HOST="0.0.0.0", LAYA_PORT="8000", LAYA_DEVICE="cuda", LAYA_PRELOAD="1")
    subprocess.Popen(["laya-serve"], env=env)
