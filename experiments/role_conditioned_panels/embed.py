"""Embed (prompt, response) with MiniLM-L6 for the PC5 slice experiments (explore_3.py, explore_pools.py).

Needs sentence-transformers (not installed with the rest; use a separate env).
  python embed.py --data tinker_pool_8models_judgments_bff.jsonl --bench bff --out emb_bff
Writes emb_bff.npy and emb_bff_ids.parquet. Text matches Ingrid's QR features:
prompt[:1200] + "\\n[RESPONSE]\\n" + response[:1200]."""
import argparse

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from data import load_judgments

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--bench", default="bff")
ap.add_argument("--condition", default="none"); ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path")
ap.add_argument("--out", required=True)
a = ap.parse_args()
d = load_judgments(a.data, a.bench, condition=a.condition, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
texts = [p[:1200] + "\n[RESPONSE]\n" + r[:1200] for p, r in zip(d.prompt, d.response)]
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
np.save(a.out + ".npy", model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False))
pd.DataFrame({"item_id": d.item_ids}).to_parquet(a.out + "_ids.parquet")
