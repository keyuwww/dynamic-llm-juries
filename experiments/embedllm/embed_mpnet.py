"""Question embeddings exactly as the EmbedLLM code does it: SentenceTransformer('all-mpnet-base-v2'), default batch
size, NO normalization. Two text variants per item:
  q   the prompt only (what the paper embeds)
  qr  prompt[:1200] + "\\n[RESPONSE]\\n" + response[:1200]  (the judge's input is the response being judged too)
Run in an env with sentence-transformers. Writes data_cache/mpnet_<bench>_<variant>.npy + _ids.parquet."""
import argparse, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "role_conditioned_panels"))
from sentence_transformers import SentenceTransformer
from data import load_judgments

here = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("--bff", required=True); ap.add_argument("--rb2", required=True); a = ap.parse_args()
os.makedirs(os.path.join(here, "data_cache"), exist_ok=True)
model = SentenceTransformer("all-mpnet-base-v2")
for bench, path in (("bff", a.bff), ("rb2safety", a.rb2)):
    d = load_judgments(path, bench, condition="none")
    texts = {"q": list(d.prompt), "qr": [p[:1200] + "\n[RESPONSE]\n" + r[:1200] for p, r in zip(d.prompt, d.response)]}
    for v, t in texts.items():
        E = model.encode(t, show_progress_bar=False)
        np.save(os.path.join(here, "data_cache", f"mpnet_{bench}_{v}.npy"), E.astype(np.float32))
        pd.DataFrame({"item_id": d.item_ids}).to_parquet(os.path.join(here, "data_cache", f"mpnet_{bench}_{v}_ids.parquet"))
        print(bench, v, E.shape, flush=True)
