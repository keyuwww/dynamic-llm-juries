"""Synchronized question bootstrap of existing readouts, conditional on selected layers.

Equal weight per judge-benchmark pair; resample questions within benchmark,
using the same multiplicities for every judge. Does not correct layer selection.
"""
import json
import numpy as np
import paper_analysis as P
from paper_data import pool_sets, add_sum, BIG


def main():
    sets = {}
    for (judge, bench), obj in pool_sets().items():
        if judge in BIG:
            continue
        rows = add_sum(obj['rows'], lambda r: r['qid'])
        scores = {m: P.per_group(rows, m, lambda r:r['qid']) for m in P.METHODS
                  if np.mean([r.get(m) is not None for r in rows]) > .9}
        common = sorted(set.intersection(*(set(v) for v in scores.values())))
        sets[judge,bench] = {m:{q:v[q] for q in common} for m,v in scores.items()}
    universes = {b:sorted({q for (j,bb),s in sets.items() if bb==b for q in s['verdict']}) for b in {b for j,b in sets}}
    rng = np.random.default_rng(42)
    result = {}
    draws = {m:[] for m in P.METHODS if m!='verdict'}
    for k in range(2001):
        weights = {b:dict(zip(qs, np.ones(len(qs)) if k==0 else rng.multinomial(len(qs), np.ones(len(qs))/len(qs)))) for b,qs in universes.items()}
        values = {m:[] for m in draws}
        for (j,b), scores in sets.items():
            totals = {m:sum((v*weights[b][q] for q,v in s.items()), np.zeros(5)) for m,s in scores.items()}
            base = totals['verdict']
            if base[1]==0 or base[3]==0:
                continue
            for m in values:
                if m in totals:
                    t=totals[m]
                    values[m].append([100*(t[0]/t[1]-base[0]/base[1]),100*(t[2]/t[3]-base[2]/base[3])])
        for m,v in values.items():
            if k==0:
                result[m]={'estimate':np.mean(v,axis=0).tolist(),'n_pairs':len(v)}
            else:
                draws[m].append(np.mean(v,axis=0))
    for m in draws:
        result[m]['ci95']=np.percentile(draws[m],[2.5,97.5],axis=0).tolist()
    out={'estimand':'equal-weight mean over observed judge-benchmark pairs; rank and best-of-n gains in pp',
         'limitation':'conditional on existing selected layers and gap-qualified pairs; no selection correction', 'results':result}
    (P.OUTD/'reviewer_cluster.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':
    main()
