import sys, json, os, statistics as st
sys.path.insert(0, '../tinker_pool')
sys.path.insert(0, '../jev_bff')
from data import load_bff, load_verdicts_items, bff_key_to_uid

items, dropped = load_verdicts_items(None, None, 'unanimous')
to_uid = bff_key_to_uid(load_bff(None))
for it in items:
    it['uid'] = to_uid.get(it['qid'], it['qid'])
by_id = {it['id']: it for it in items}

def pfp(v): return 1 if v >= 0.5 else 0
def fb(v):
    if isinstance(v, (int, bool)): return int(bool(v))
    return 1 if str(v) == 'CORRECT' else 0
def last_user_len(conv):
    u = [m['content'] for m in conv if m['role'] == 'user']
    return len(u[-1]) if u else 0
def last_assistant_len(conv):
    a = [m['content'] for m in conv if m['role'] == 'assistant']
    return len(a[-1]) if a else 0

cells = [
    ('significance_results/bff_rubric_qwen3.5-4b.json', 'qwen3.5-4b bff-rubric'),
    ('significance_results/bff_standard_nvidia-nemotron-3-nano-30b-a3b-bf16.json', 'nemotron3-nano-30b bff-standard'),
    ('significance_results/bff_standard_gpt-oss-120b.json', 'gpt-oss-120b bff-standard'),
]

for sigpath, label in cells:
    sig = json.load(open(sigpath))
    pilot = json.load(open(sig['pilot']))
    L = sig['modal_winning_layer']
    pcn_f, pred_f = sig['pcn_field'], sig['pred_field']
    rows = []
    for it in pilot['items']:
        src = by_id.get(it['id'])
        if src is None:
            continue
        gold = it['gold']
        layer_correct = pfp(it[pcn_f][L]) == gold
        final_correct = fb(it[pred_f]) == gold
        cat = 'layer_rescues' if (layer_correct and not final_correct) else \
              'final_better' if (final_correct and not layer_correct) else \
              'both_right' if (layer_correct and final_correct) else 'both_wrong'
        rows.append(dict(cat=cat, ulen=last_user_len(src['conv']), alen=last_assistant_len(src['conv']),
                          examinee=src.get('examinee')))
    print(f"\n=== {label} (layer {L}/{pilot['n_layers']}), matched {len(rows)}/{len(pilot['items'])} ===")
    for cat in ['layer_rescues', 'final_better', 'both_right', 'both_wrong']:
        sub = [r for r in rows if r['cat'] == cat]
        if not sub:
            continue
        ulens = [r['ulen'] for r in sub]
        alens = [r['alen'] for r in sub]
        exam = {}
        for r in sub:
            exam[r['examinee']] = exam.get(r['examinee'], 0) + 1
        top = sorted(exam.items(), key=lambda x: -x[1])[:3]
        print(f"  {cat:14s} n={len(sub):3d}  mean_user_len={st.mean(ulens):6.0f}  mean_resp_len={st.mean(alens):6.0f}  top_examinees={top}")
