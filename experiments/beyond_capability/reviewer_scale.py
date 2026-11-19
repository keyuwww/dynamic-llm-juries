"""Compare Llama sizes on identical available failed-question candidate sets."""
import json
import numpy as np
from paper_data import sm_sets
from paper_analysis import per_group, OUTD


def main():
    sets = sm_sets()
    out = {}
    for bench in ('math','mmlu'):
        data = {j:r for (j,b,a),r in sets.items() if b==bench and a=='qwen3.5-4b' and j in
                ('llama3.2-1b','llama3.2-3b','llama3.1-8b','llama3.1-70b')}
        if 'llama3.1-70b' not in data or len(data)<2:
            continue
        ids = set.intersection(*({r['aid'] for r in rows} for rows in data.values()))
        counts = {j:per_group([r for r in rows if r['aid'] in ids], 'verdict', lambda r:(r['qid'],r['src'])) for j,rows in data.items()}
        qs = sorted(set.intersection(*(set(v) for v in counts.values())))
        arrays = {j:np.array([v[q] for q in qs]) for j,v in counts.items()}
        rng = np.random.default_rng(7)
        idx = rng.integers(0,len(qs),(2000,len(qs)))
        scores = {j:100*v[:,0].sum()/v[:,1].sum() for j,v in arrays.items()}
        bs = {j:100*v[idx,0].sum(axis=1)/v[idx,1].sum(axis=1) for j,v in arrays.items()}
        out[bench]={'n_questions':len(qs),'n_common_answers':len(ids),'rank':scores,'70b_minus_smaller':{
            j:{'difference':scores['llama3.1-70b']-s,'ci95':np.percentile(bs['llama3.1-70b']-bs[j],[2.5,97.5]).tolist()}
            for j,s in scores.items() if j!='llama3.1-70b'}}
    (OUTD/'reviewer_scale.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':
    main()
