# Quick look (in-sample thresholds): cheap judge answers; escalate its most-doubted q share to the best judge.
import sys; sys.path.insert(0,'.')
import numpy as np
from sensor_router import load, BENCHES
from order_consistency import SHORT
for b in BENCHES:
    S,R0,R1,C,g,cost = load(b)
    best = S.mean().idxmax(); cb = cost[best]
    print(f"\n{b}: best {SHORT[best]} acc {S[best].mean():.3f} cost ${cb*1000:.2f}/1k")
    for c in S.columns:
        if c == best or cost[c] >= cb: continue
        d = (-C[c]).rank(pct=True)
        line = []
        for q in [0, .2, .4, .6]:
            esc = d > 1 - q
            acc = np.where(esc, S[best], S[c]).mean(); cst = cost[c] + esc.mean()*cb
            line.append(f"q={q:.1f}: {acc:.3f} ${cst*1000:.2f}")
        print(f"  {SHORT[c]:9s} " + " | ".join(line))
