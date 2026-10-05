import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

here = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(here, "results", "accuracy_comparison.csv"))

benchmarks = list(dict.fromkeys(df.benchmark))
strategies = list(dict.fromkeys(df.strategy))

x = np.arange(len(benchmarks))
w = 0.2
fig, ax = plt.subplots(figsize=(9, 5))
for j, s in enumerate(strategies):
    acc = [df[(df.benchmark == b) & (df.strategy == s)].acc.iloc[0] for b in benchmarks]
    ax.bar(x + (j - 1.5) * w, acc, w, label=s)

ax.set_xticks(x)
ax.set_xticklabels(benchmarks)
ax.set_ylabel("Held-out accuracy")
ax.set_ylim(0.7, 1.0)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(here, "results", "accuracy_comparison.png"), dpi=150)
