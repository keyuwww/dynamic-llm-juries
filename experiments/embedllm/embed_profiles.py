"""Embed the short judge profile texts (judge_profiles.json) with all-mpnet-base-v2, like IRT-Router embeds LLM profiles
(there with bert-base-uncased). Profiles are written from the model names only (developer, family, size).
Run in an env with sentence-transformers. Writes data_cache/judge_profiles_mpnet.npy (rows in data.COST_PER_CALL order)."""
import json, os
import numpy as np
from sentence_transformers import SentenceTransformer

here = os.path.dirname(os.path.abspath(__file__))
prof = json.load(open(os.path.join(here, "judge_profiles.json")))
order = ["gpt-oss-120b", "gpt-oss-20b", "deepseek-v3.1", "qwen3.6-35b-a3b", "qwen3.5-4b", "nemotron3-super-120b", "qwen3.5-9b", "nemotron3-nano-30b"]
E = SentenceTransformer("all-mpnet-base-v2").encode([prof[j] for j in order], show_progress_bar=False)
os.makedirs(os.path.join(here, "data_cache"), exist_ok=True)
np.save(os.path.join(here, "data_cache", "judge_profiles_mpnet.npy"), E.astype(np.float32)); print(E.shape)
