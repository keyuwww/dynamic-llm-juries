# sourced by the job scripts (run from the job's submit directory .../beyond_capability_steer/outer)
set +u; source /etc/profile; set -u
declare -A MODEL=([llama3.1-8b]=meta-llama/Llama-3.1-8B-Instruct [llama3.2-3b]=meta-llama/Llama-3.2-3B-Instruct
  [llama3.2-1b]=meta-llama/Llama-3.2-1B-Instruct [qwen2.5-7b]=Qwen/Qwen2.5-7B-Instruct [qwen3.5-4b]=Qwen/Qwen3.5-4B
  [phi4-mini]=microsoft/Phi-4-mini-instruct [mistral-7b]=mistralai/Mistral-7B-Instruct-v0.3
  [granite3.3-8b]=ibm-granite/granite-3.3-8b-instruct)
declare -A ITEMS=([mmlu]=mmlu_full_items.jsonl.gz [math]=math_full_items.jsonl.gz [bbeh]=bbeh_items.jsonl.gz)
LC=/tmp/bco_${SLURM_JOB_ID}; mkdir -p $LC
# task-specific caches only; the shared HF cache (weights + token) sits one level up, as for the 70B jobs
export HF_HOME=$PWD/../hf_cache HF_HUB_OFFLINE=1 XDG_CACHE_HOME=$LC TRITON_CACHE_DIR=$LC/triton VLLM_CACHE_ROOT=$LC/vllm \
       PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HOME=$PWD/../home
