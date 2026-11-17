"""Second answering model for the same-model test (MMLU, MATH): OLMo-2-7B-Instruct, a family none of the judges or the
first answering model (Qwen3.5-4B) belongs to, answers each question of inputs/sm_{mmlu,math}_q.jsonl 12 times
(T = 0.7, thinking-free chat model, at most 2560 new tokens (4096 context); hitting the cap = not clean).
-> out/esolves_sm_{bench}_q_olmo2-7b.jsonl in the same format as the Qwen3.5-4B samples, so sm_build_items.py and the
GLM grader (bc_jobs.py --phase egrade) read it unchanged.

  MODAL_PROFILE=ingridchien .venv/bin/modal run experiments/beyond_capability/sm2_gen_modal.py
"""
import json
import pathlib

import modal

_here = pathlib.Path(__file__).resolve()
M2, HF = "olmo2-7b", "allenai/OLMo-2-1124-7B-Instruct"
image = modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.11").pip_install("vllm")
for b in ("mmlu", "math"):
    image = image.add_local_file(_here.parent / "inputs" / f"sm_{b}_q.jsonl", f"/root/sm_{b}_q.jsonl")
app = modal.App("dlj-sm2-gen", image=image)
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)


@app.function(gpu="H100", timeout=3 * 3600, volumes={"/root/.cache/huggingface": hf_cache},
              secrets=[modal.Secret.from_name("huggingface")])
def gen(bench: str, n: int = 12) -> str:
    from vllm import LLM, SamplingParams
    qs = [json.loads(l) for l in open(f"/root/sm_{bench}_q.jsonl")]
    llm = LLM(HF, max_model_len=4096, gpu_memory_utilization=0.9, seed=0)
    tok = llm.get_tokenizer()
    prompts = [tok.apply_chat_template([{"role": "user", "content": q["prompt"]}], tokenize=False, add_generation_prompt=True)
               for q in qs]
    keep = [i for i, p in enumerate(prompts) if len(tok(p).input_ids) < 1500]
    outs = llm.generate([prompts[i] for i in keep], SamplingParams(n=n, temperature=0.7, max_tokens=2560, seed=0))
    lines = []
    for i, o in zip(keep, outs):
        q = qs[i]
        lines.append(json.dumps(dict(cache_key=f"{M2}|{q['id']}", model=M2, qid=q["id"],
                                     samples=[dict(text=c.text, clean=c.finish_reason == "stop", n_out=len(c.token_ids))
                                              for c in o.outputs])))
    return "\n".join(lines) + "\n"


@app.local_entrypoint()
def main():
    out = _here.parent / "out"
    for b, data in zip(("mmlu", "math"), gen.map(["mmlu", "math"])):
        f = out / f"esolves_sm_{b}_q_{M2}.jsonl"
        f.write_text(data)
        print(f"saved {f} ({data.count(chr(10))} questions)")
