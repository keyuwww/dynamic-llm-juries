project: olmo3-think-stages
script: run.sh
hardware: a100
time: "05:00:00"
docker:
  image: vllm/vllm-openai:v0.11.0
  requires_accelerator: cuda
