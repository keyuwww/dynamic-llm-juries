"""Force the cheapest judge to be the first panel member, then grow greedily (teammate/Arijit suggestion)."""
import argparse, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import drop_judges, load_judgments
from evaluate import pooled_bootstrap, run_all_repeats
from majority import run_all_repeats_mv
from splits import make_3way_splits

ap = argparse.ArgumentParser()
ap.add_argument("--bff", required=True); ap.add_argument("--rb2", required=True)
ap.add_argument("--verdicts-path"); ap.add_argument("--rb2-path"); ap.add_argument("--exclude", nargs="*", default=[])
a = ap.parse_args(); pd.set_option("display.width", 200)
rows = []
for label, path, bench, cond in [("BFF none", a.bff, "bff", "none"), ("BFF human", a.bff, "bff", "human"), ("RB2 safety", a.rb2, "rb2safety", "none")]:
    d = load_judgments(path, bench, condition=cond, verdicts_path=a.verdicts_path, rb2_path=a.rb2_path)
    if a.exclude:
        d = drop_judges(d, a.exclude)
    sp = make_3way_splits(d.groups, 0, 20)
    cheapest = min(d.cost, key=d.cost.get)
    for rule, runner in (("eta", run_all_repeats), ("majority", run_all_repeats_mv)):
        for tag, first in (("greedy (default)", None), (f"cheapest first ({cheapest})", cheapest)):
            o = runner(d, sp, first_judge=first, verbose=False)
            r = o["results"]; p = r[r.strategy == "path_a_panel"]
            b = pooled_bootstrap(o["pooled"], d.groups, "path_a_panel", "static_top3")
            rows.append(dict(setting=label, rule=rule, start=tag, acc=p.acc.mean(), cost=p.cost.mean(), panel=p.panel_size.mean(),
                             top3_acc=r[r.strategy == "static_top3"].acc.mean(), vs_top3=b["diff"], ci=f"[{b['lo']:+.3f},{b['hi']:+.3f}]"))
print(pd.DataFrame(rows).round(4).to_string(index=False))
