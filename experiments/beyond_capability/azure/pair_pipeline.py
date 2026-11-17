"""One (judge, benchmark) pair, end to end, with the layer rule fixed in advance (out_allpairs/RULE.md):

  1. capture   one pass per answer: hidden state at "VERDICT:" (every 2nd layer) + unedited verdict margin
  2. gap       per layer, question-centred "right minus wrong" direction learned on one half of the questions, scored on
               the other half (KNOWS = held-out within-question ranking); SAYS = ranking of the unedited verdict.
               GAP = 100 x (max over layers of KNOWS - SAYS). Stop here unless GAP > 5.
  3. push      on 400 random answers (each with the direction from the other half): accept rate at -8 sd and +8 sd along
               the direction at every candidate layer (every 2nd layer except 0 and the last). No labels used.
  4. choose    among layers whose accept rate rises >= 10 points from -8 to +8, the one with the highest KNOWS;
               if none, the highest-KNOWS layer (marked "no layer responds").
  5. final     all answers at the chosen layer: unedited, add -8 / +8 sd, stretch x11 along the judge direction, and
               stretch x11 along a random direction.                                -> final_<tag>.jsonl, choice_<tag>.json
  6. solve     (optional) the judge answers the benchmark's questions itself, thinking off, T = 0.7, one sample,
               at most --max-new tokens (hitting the cap = wrong).                  -> esolves_<tag>.jsonl

Hybrid-attention models (Qwen3.5) re-run the whole prompt for every edit; others re-run only the last token with the
prompt's KV cache (checked equal to a full re-run, to bf16 rounding, in layer_sweep_modal.py --phase smoke).
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

import numpy as np

from dir_capture import build_ids, setup, verdict_ids


def within_auc(y, s, q):
    by = collections.defaultdict(lambda: ([], []))
    for yi, si, g in zip(y, s, q):
        by[g][int(yi)].append(si)
    num = den = 0.0
    for neg, pos in by.values():
        for a in pos:
            for b in neg:
                num += 1.0 if a > b else 0.5 if a == b else 0.0
                den += 1
    return num / den if den else float("nan")


class Judge:
    def __init__(self, model_name, use_cache):
        import torch
        self.torch = torch
        self.tok, self.model, self.layers = setup(model_name)
        self.t1, self.t2 = verdict_ids(self.tok)
        self.use_cache = use_cache
        self.ctx = self.model.config.get_text_config().max_position_embeddings
        self.state = {"L": None}
        for i, layer in enumerate(self.layers):
            layer.register_forward_hook(self._hook(i + 1))  # hidden_states[L] = output of decoder layer L-1

    def _hook(self, L):
        def hook(module, inp, o):
            st = self.state
            if st["L"] != L:
                return o
            h = o[0] if isinstance(o, tuple) else o
            h = h.clone()
            if st.get("allpos"):  # diagnostic: the same push at every token position
                h[0] = (h[0].float() + st["s"] * st["sd"] * st["v"].to(h.device)).to(h.dtype)
                return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
            x = h[0, -1].float()
            v = st["v"].to(x.device)  # the edited layer may sit on another GPU when the judge is split
            if st["kind"] == "add":
                x = x + st["s"] * st["sd"] * v
            else:
                x = x + st["s"] * ((x @ v) - st["mu"]) * v
            h[0, -1] = x.to(h.dtype)
            return (h,) + tuple(o[1:]) if isinstance(o, tuple) else h
        return hook

    def prepare(self, ids):
        """returns a handle for repeated edited reads of this prompt's verdict."""
        if not self.use_cache:
            return None
        self.state["L"] = None
        with self.torch.no_grad():
            o = self.model(input_ids=self.torch.tensor([ids[:-1]], device="cuda"), use_cache=True, logits_to_keep=1)
        return o.past_key_values

    def read(self, ids, cache, edit=None, hidden=False):
        """verdict margin (and hidden states) with an optional edit dict(L, kind, s, v, mu, sd)."""
        torch = self.torch
        self.state = dict(edit) if edit else {"L": None}
        with torch.no_grad():
            if self.use_cache:
                o = self.model(input_ids=torch.tensor([ids[-1:]], device="cuda"), past_key_values=cache, use_cache=True,
                               logits_to_keep=1, output_hidden_states=hidden)
                cache.crop(len(ids) - 1)
            else:
                o = self.model(input_ids=torch.tensor([ids], device="cuda"), logits_to_keep=1, output_hidden_states=hidden)
        self.state = {"L": None}
        lg = o.logits[0, -1].float()
        return float(lg[self.t1] - lg[self.t2]), (o.hidden_states if hidden else None)

    def read_full(self, ids, edit):
        """whole-prompt forward pass (needed when the edit touches every position)."""
        torch = self.torch
        self.state = dict(edit)
        with torch.no_grad():
            o = self.model(input_ids=torch.tensor([ids], device="cuda"), logits_to_keep=1)
        self.state = {"L": None}
        lg = o.logits[0, -1].float()
        return float(lg[self.t1] - lg[self.t2])


def load_items(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(l) for l in f if json.loads(l)["mode"] == "J"]


def run_pair(a):
    torch = __import__("torch")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    J = Judge(a.model, use_cache=not a.no_cache)
    rows = load_items(a.items)
    if a.limit:
        rows = rows[: a.limit]
    ids_all = [build_ids(J.tok, r) for r in rows]
    keepr = [i for i, ids in enumerate(ids_all) if len(ids) < J.ctx - 8]
    skipped = len(rows) - len(keepr)
    rows, ids_all = [rows[i] for i in keepr], [ids_all[i] for i in keepr]
    n = len(J.layers)
    kept = sorted(set(range(0, n + 1, 2)) | {n})
    cand = [L for L in kept if 0 < L < n]
    # ---- 1. capture
    hfile = out / f"hidden_{a.tag}.npy"
    mfile = out / f"meta_{a.tag}.jsonl"
    if not (out / f"captured_{a.tag}").exists():
        d = J.model.config.get_text_config().hidden_size
        H = np.lib.format.open_memmap(hfile, mode="w+", dtype=np.float16, shape=(len(rows), len(kept), d))
        with open(mfile, "w") as meta:
            for i, (r, ids) in enumerate(zip(rows, ids_all)):
                cache = J.prepare(ids)
                m, hs = J.read(ids, cache, hidden=True)
                H[i] = torch.stack([hs[l][0, -1] for l in kept]).float().cpu().numpy().astype(np.float16)
                meta.write(json.dumps({k: r[k] for k in ("qid", "aid", "gold", "src")} | dict(margin=m, n_tok=len(ids))) + "\n")
                del cache, hs
                if (i + 1) % 200 == 0:
                    print(f"  capture {a.tag}: {i + 1}/{len(rows)}", flush=True)
        H.flush()
        (out / f"captured_{a.tag}").write_text("ok")
        a.commit()
    if a.capture_only:
        return None
    H = np.load(hfile, mmap_mode="r")
    meta = [json.loads(l) for l in open(mfile)]
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    rng = np.random.default_rng(0)  # same split recipe as stretch_pipeline.py
    h1q = set(rng.permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    # ---- 2. gap
    knows, dirs = {}, {}
    for L in cand:
        X = np.asarray(H[:, kept.index(L)], np.float32)
        Xc = X.copy()
        for g in uq:
            k = q == g
            Xc[k] -= X[k].mean(0)
        s = np.zeros(len(y))
        for learn, mask in (("h1", h1), ("h2", ~h1)):
            v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
            v /= np.linalg.norm(v) + 1e-9
            r = np.random.default_rng(1000 + L + (learn == "h2")).normal(size=v.shape[0])
            r /= np.linalg.norm(r)
            s[~mask] = X[~mask] @ v
            for name, dv in (("Jc", v), ("Rc", r)):  # applied to the OTHER half
                p = X[mask] @ dv
                dirs[(L, name, "h2" if learn == "h1" else "h1")] = (dv, float(p.mean()), float(p.std()))
        knows[L] = within_auc(y, s, q)
    says = within_auc(y, np.array([m["margin"] for m in meta]), q)
    Lmax = max(knows, key=knows.get)
    gap = 100 * (knows[Lmax] - says)
    choice = dict(n_answers=len(meta), skipped_too_long=skipped, n_layers=n, knows=knows, says=says, gap=gap,
                  best_knows_layer=Lmax)
    print(f"  {a.tag}: SAYS {says:.3f}, best KNOWS {knows[Lmax]:.3f} at layer {Lmax}, GAP {gap:+.1f}", flush=True)
    if gap <= 5 and not a.force:
        choice["stopped"] = "gap <= 5"
        json.dump(choice, open(out / f"choice_{a.tag}.json", "w"), indent=1)
        return choice

    def edit(L, name, half, kind, s):
        v, mu, sd = dirs[(L, name, half)]
        return dict(L=L, kind=kind, s=s, v=torch.tensor(v, dtype=torch.float32, device="cuda"), mu=mu, sd=sd)
    half_of = lambda i: "h1" if h1[i] else "h2"  # noqa: E731
    # ---- 3. push test (no labels)
    sub = sorted(np.random.default_rng(1).choice(len(meta), min(400, len(meta)), replace=False).tolist())
    acc = {L: [0, 0] for L in cand}
    dm = {L: 0.0 for L in cand}  # summed verdict-score change from -8 to +8 sd
    for j, i in enumerate(sub):
        cache = J.prepare(ids_all[i])
        for L in cand:
            ms = []
            for k, s in ((0, -8.0), (1, 8.0)):
                m, _ = J.read(ids_all[i], cache, edit(L, "Jc", half_of(i), "add", s))
                acc[L][k] += m > 0
                ms.append(m)
            dm[L] += ms[1] - ms[0]
        del cache
        if (j + 1) % 100 == 0:
            print(f"  push {a.tag}: {j + 1}/{len(sub)}", flush=True)
    marg = np.array([m["margin"] for m in meta])
    wsd = float(np.sqrt(np.mean([np.var(marg[q == g]) for g in uq if (q == g).sum() > 1])))
    push = {L: dict(minus8=100 * acc[L][0] / len(sub), plus8=100 * acc[L][1] / len(sub),
                    sensitivity=dm[L] / len(sub) / 16 / wsd) for L in cand}
    resp_acc = [L for L in cand if push[L]["plus8"] - push[L]["minus8"] >= 10]
    resp_score = [L for L in cand if push[L]["sensitivity"] >= 0.05]
    resp = resp_score if a.rule == "v2" else resp_acc
    chosen = max(resp, key=knows.get) if resp else Lmax
    choice.update(push=push, responding_layers=resp, chosen_layer=chosen, rule="responds" if resp else "no layer responds",
                  rule_version=a.rule, responding_accept=resp_acc, responding_score=resp_score,
                  chosen_v1=max(resp_acc, key=knows.get) if resp_acc else Lmax)
    print(f"  {a.tag}: responding layers {resp}; chosen layer {chosen}", flush=True)
    json.dump(choice, open(out / f"choice_{a.tag}.json", "w"), indent=1)
    a.commit()
    # ---- 5. final pass at the chosen layer
    edits = [("Jc", "add", -8.0), ("Jc", "add", 8.0), ("Jc", "amplify", 10.0), ("Rc", "amplify", 10.0),
             ("Jc", "amplify", 3.0), ("Jc", "amplify", 20.0)]  # x4 / x21: secondary (strength), x11 is primary
    with open(out / f"final_{a.tag}.jsonl", "w") as fh:
        for i, (m0, ids) in enumerate(zip(meta, ids_all)):
            cache = J.prepare(ids)
            res = {"none": m0["margin"]}
            for name, kind, s in edits:
                res[f"{name}:{kind}:{s}"] = J.read(ids, cache, edit(chosen, name, half_of(i), kind, s))[0]
            fh.write(json.dumps({k: m0[k] for k in ("qid", "aid", "gold", "src")} | dict(layer=chosen, margins=res)) + "\n")
            del cache
            if (i + 1) % 200 == 0:
                print(f"  final {a.tag}: {i + 1}/{len(meta)}", flush=True)
    a.commit()
    return choice


def diagnose(a):
    """Why does (or doesn't) a pair's verdict respond? Needs the pair's capture (hidden_/meta_) in --out.
    Per candidate layer:
      corr          within-question correlation between the answer's position along the held-out direction and the
                    unedited verdict margin (does the verdict already read this direction, and with which sign?)
      src_share     share of the direction's within-question spread explained by which model wrote the answer
      push_last     accept rate at -8 / +8 sd, edit at the last token only (as in the main run)
      push_all      the same push applied at every token position (tests whether later layers re-read the answer
                    from earlier tokens and overwrite a last-token edit)
    -> diag_<tag>.json"""
    torch = __import__("torch")
    out = Path(a.out)
    J = Judge(a.model, use_cache=not a.no_cache)
    rows = load_items(a.items)
    ids_all = [build_ids(J.tok, r) for r in rows]
    keepr = [i for i, ids in enumerate(ids_all) if len(ids) < J.ctx - 8]
    ids_all = [ids_all[i] for i in keepr]
    n = len(J.layers)
    kept = sorted(set(range(0, n + 1, 2)) | {n})
    cand = [L for L in kept if 0 < L < n]
    H = np.load(out / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(out / f"meta_{a.tag}.jsonl")]
    assert len(meta) == len(ids_all)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    src = np.array([m["src"] for m in meta])
    marg = np.array([m["margin"] for m in meta])
    uq = sorted(set(q))
    rng = np.random.default_rng(0)
    h1q = set(rng.permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])

    def qcenter(x):
        x = x.astype(float).copy()
        for g in uq:
            k = q == g
            x[k] -= x[k].mean()
        return x
    mc = qcenter(marg)
    stats, dirs = {}, {}
    for L in cand:
        X = np.asarray(H[:, kept.index(L)], np.float32)
        Xc = X.copy()
        for g in uq:
            k = q == g
            Xc[k] -= X[k].mean(0)
        s = np.zeros(len(y))
        for learn, mask in (("h1", h1), ("h2", ~h1)):
            v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
            v /= np.linalg.norm(v) + 1e-9
            s[~mask] = X[~mask] @ v
            p = X[mask] @ v
            dirs[(L, "h2" if learn == "h1" else "h1")] = (v, float(p.mean()), float(p.std()))
        sc = qcenter(s)
        cell = {}  # (question, source) means of the centred projection
        for i in range(len(sc)):
            cell.setdefault((q[i], src[i]), []).append(sc[i])
        between = sum(len(v) * np.mean(v) ** 2 for v in cell.values())
        stats[L] = dict(corr=float(np.corrcoef(sc, mc)[0, 1]), src_share=float(between / (sc ** 2).sum()))
    sub = sorted(np.random.default_rng(1).choice(len(meta), min(a.n_push, len(meta)), replace=False).tolist())
    cnt = {L: np.zeros(4) for L in cand}
    for j, i in enumerate(sub):
        half = "h1" if h1[i] else "h2"
        cache = J.prepare(ids_all[i])
        for L in cand:
            v, mu, sd = dirs[(L, half)]
            vt = torch.tensor(v, dtype=torch.float32, device="cuda")
            for k, (allpos, s_) in enumerate(((False, -8.0), (False, 8.0), (True, -8.0), (True, 8.0))):
                e = dict(L=L, kind="add", s=s_, v=vt, mu=mu, sd=sd, allpos=allpos)
                m = J.read_full(ids_all[i], e) if allpos else J.read(ids_all[i], cache, e)[0]
                cnt[L][k] += m > 0
        del cache
        if (j + 1) % 50 == 0:
            print(f"  diagnose {a.tag}: {j + 1}/{len(sub)}", flush=True)
    for L in cand:
        c = 100 * cnt[L] / len(sub)
        stats[L].update(push_last=[float(c[0]), float(c[1])], push_all=[float(c[2]), float(c[3])])
    json.dump({str(k): v for k, v in stats.items()}, open(out / f"diag_{a.tag}.json", "w"), indent=1)
    print(f"done: diagnose {a.tag}", flush=True)


def extra(a):
    """Judge new answers (--extra-items) at --layer with the pair's own directions: each question gets the direction
    learned on the half of the ORIGINAL questions that does not contain it (same split as the main run).
    -> extra_<tag>.jsonl (same margins keys as final_<tag>.jsonl)"""
    torch = __import__("torch")
    out = Path(a.out)
    H = np.load(out / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(out / f"meta_{a.tag}.jsonl")]
    kept = sorted(set(range(0, a.n_layers + 1, 2)) | {a.n_layers})
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    rng = np.random.default_rng(0)
    h1q = set(rng.permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    L = a.layer
    X = np.asarray(H[:, kept.index(L)], np.float32)
    Xc = X.copy()
    for g in uq:
        k = q == g
        Xc[k] -= X[k].mean(0)
    dirs = {}
    for learn, mask in (("h1", h1), ("h2", ~h1)):
        v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
        v /= np.linalg.norm(v) + 1e-9
        r = np.random.default_rng(1000 + L + (learn == "h2")).normal(size=v.shape[0])
        r /= np.linalg.norm(r)
        for name, dv in (("Jc", v), ("Rc", r)):
            p_ = X[mask] @ dv
            dirs[(name, "h2" if learn == "h1" else "h1")] = (torch.tensor(dv, dtype=torch.float32, device="cuda"),
                                                             float(p_.mean()), float(p_.std()))
    J = Judge(a.model, use_cache=not a.no_cache)
    rows = load_items(a.extra_items)
    edits = [("Jc", "add", -8.0), ("Jc", "add", 8.0), ("Jc", "amplify", 10.0), ("Rc", "amplify", 10.0),
             ("Jc", "amplify", 3.0), ("Jc", "amplify", 20.0)]
    with open(out / f"{a.prefix}_{a.tag}.jsonl", "w") as fh:
        for i, r in enumerate(rows):
            ids = build_ids(J.tok, r)
            if len(ids) >= J.ctx - 8:
                continue
            half = "h1" if r["qid"] in h1q else "h2"  # direction from the other half
            cache = J.prepare(ids)
            m0, hs = J.read(ids, cache, hidden=a.with_proj)
            res = {"none": m0}
            extra_fields = {}
            if a.with_proj:  # position along the direction, unedited (same precision as the capture)
                h = hs[L][0, -1].float().cpu().numpy().astype(np.float16).astype(np.float32)
                extra_fields["proj"] = float(h @ dirs[("Jc", half)][0].cpu().numpy())
                del hs
            for name, kind, s in edits:
                v, mu, sd = dirs[(name, half)]  # keyed by the half it is applied to (learned on the other)
                res[f"{name}:{kind}:{s}"] = J.read(ids, cache, dict(L=L, kind=kind, s=s, v=v, mu=mu, sd=sd))[0]
            fh.write(json.dumps({k: r[k] for k in ("qid", "aid", "gold", "src")} | dict(layer=L, margins=res) | extra_fields) + "\n")
            del cache
            if (i + 1) % 200 == 0:
                print(f"  extra {a.tag}: {i + 1}/{len(rows)}", flush=True)
    print("done: extra", flush=True)


def extra_direct(a):
    """Position of each same-model answer (--extra-items) along the pair's correctness direction at --layer, no edit:
    one forward pass per answer; direction learned on the half of the ORIGINAL questions that does not contain the
    question (same split as extra()). -> xdirect_<tag>.jsonl (aid, qid, gold, src, proj, margin)"""
    torch = __import__("torch")
    out = Path(a.out)
    H = np.load(out / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(out / f"meta_{a.tag}.jsonl")]
    kept = sorted(set(range(0, a.n_layers + 1, 2)) | {a.n_layers})
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    L = a.layer
    X = np.asarray(H[:, kept.index(L)], np.float32)
    Xc = X.copy()
    for g in uq:
        Xc[q == g] -= X[q == g].mean(0)
    v = {}
    for learn, mask in (("h1", h1), ("h2", ~h1)):
        d = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
        v["h2" if learn == "h1" else "h1"] = d / (np.linalg.norm(d) + 1e-9)  # keyed by the half it is applied to
    J = Judge(a.model, use_cache=not a.no_cache)
    rows = load_items(a.extra_items)
    with open(out / f"xdirect_{a.tag}.jsonl", "w") as fh:
        for i, r in enumerate(rows):
            ids = build_ids(J.tok, r)
            if len(ids) >= J.ctx - 8:
                continue
            cache = J.prepare(ids)
            m, hs = J.read(ids, cache, hidden=True)
            h = hs[L][0, -1].float().cpu().numpy().astype(np.float16).astype(np.float32)  # same precision as capture
            half = "h1" if r["qid"] in h1q else "h2"
            fh.write(json.dumps({k: r[k] for k in ("qid", "aid", "gold", "src")} | dict(proj=float(h @ v[half]), margin=m)) + "\n")
            del cache, hs
            if (i + 1) % 500 == 0:
                print(f"  xdirect {a.tag}: {i + 1}/{len(rows)}", flush=True)
    print("done: extra_direct", flush=True)


def sweep(a):
    """Exploratory: every candidate layer, all answers: unedited, add -8 / +8 sd, x11 along the judge direction and a
    random direction (directions rebuilt from the pair's capture, each half from the other). -> sweep_<tag>.jsonl"""
    torch = __import__("torch")
    out = Path(a.out)
    H = np.load(out / f"hidden_{a.tag}.npy", mmap_mode="r")
    meta = [json.loads(l) for l in open(out / f"meta_{a.tag}.jsonl")]
    J = Judge(a.model, use_cache=not a.no_cache)
    n = len(J.layers)
    kept = sorted(set(range(0, n + 1, 2)) | {n})
    cand = [L for L in kept if 0 < L < n]
    rows = load_items(a.items)
    ids_all = [build_ids(J.tok, r) for r in rows]
    ids_all = [x for x in ids_all if len(x) < J.ctx - 8]
    assert len(ids_all) == len(meta)
    y = np.array([m["gold"] for m in meta])
    q = np.array([m["qid"] for m in meta])
    uq = sorted(set(q))
    h1q = set(np.random.default_rng(0).permutation(uq)[: len(uq) // 2])
    h1 = np.array([x in h1q for x in q])
    dirs = {}
    for L in cand:
        X = np.asarray(H[:, kept.index(L)], np.float32)
        Xc = X.copy()
        for g in uq:
            k = q == g
            Xc[k] -= X[k].mean(0)
        for learn, mask in (("h1", h1), ("h2", ~h1)):
            v = Xc[mask][y[mask] == 1].mean(0) - Xc[mask][y[mask] == 0].mean(0)
            v /= np.linalg.norm(v) + 1e-9
            r = np.random.default_rng(1000 + L + (learn == "h2")).normal(size=v.shape[0])
            r /= np.linalg.norm(r)
            for name, dv in (("Jc", v), ("Rc", r)):
                p_ = X[mask] @ dv
                dirs[(L, name, "h2" if learn == "h1" else "h1")] = (
                    torch.tensor(dv, dtype=torch.float32, device="cuda"), float(p_.mean()), float(p_.std()))
    edits = [("Jc", "add", -8.0), ("Jc", "add", 8.0), ("Jc", "amplify", 10.0), ("Rc", "amplify", 10.0)]
    with open(out / f"sweep_{a.tag}.jsonl", "w") as fh:
        for i, (m0, ids) in enumerate(zip(meta, ids_all)):
            half = "h1" if h1[i] else "h2"
            cache = J.prepare(ids)
            for L in cand:
                res = {"none": m0["margin"]}
                for name, kind, s in edits:
                    v, mu, sd = dirs[(L, name, half)]
                    res[f"{name}:{kind}:{s}"] = J.read(ids, cache, dict(L=L, kind=kind, s=s, v=v, mu=mu, sd=sd))[0]
                fh.write(json.dumps({k: m0[k] for k in ("qid", "aid", "gold", "src")} | dict(layer=L, margins=res)) + "\n")
            del cache
            if (i + 1) % 200 == 0:
                print(f"  sweep {a.tag}: {i + 1}/{len(meta)}", flush=True)
    print("done: sweep", flush=True)


def solve(a):
    """the judge answers questions itself: --qfile rows with id + messages (or prompt)."""
    torch = __import__("torch")
    tok, model, _ = setup(a.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    qs = [json.loads(l) for l in open(a.qfile)]
    if a.limit:
        qs = qs[: a.limit]
    fpath = Path(a.out) / f"esolves_{a.tag}.jsonl"
    done = {json.loads(l)["qid"] for l in open(fpath)} if fpath.exists() else set()
    todo = [q for q in qs if q["id"] not in done]
    stops = {tok.eos_token_id}
    for t in ("<|eot_id|>", "<|im_end|>", "<|end|>", "<|end_of_text|>"):
        tid = tok.convert_tokens_to_ids(t)
        if isinstance(tid, int) and tid != tok.unk_token_id:
            stops.add(tid)
    stops.discard(None)
    enc = {q["id"]: build_ids(tok, dict(messages=q.get("messages") or [{"role": "user", "content": q["prompt"]}], suffix=""))
           for q in todo}
    todo.sort(key=lambda q: len(enc[q["id"]]))
    fh = open(fpath, "a")
    for b0 in range(0, len(todo), a.batch):
        batch = todo[b0:b0 + a.batch]
        e = [enc[q["id"]] for q in batch]
        n = max(map(len, e))
        ids = torch.full((len(e), n), tok.pad_token_id, dtype=torch.long)
        att = torch.zeros((len(e), n), dtype=torch.long)
        for i, x in enumerate(e):
            ids[i, n - len(x):] = torch.tensor(x)
            att[i, n - len(x):] = 1
        with torch.no_grad():
            g = model.generate(input_ids=ids.cuda(), attention_mask=att.cuda(), do_sample=True, temperature=0.7,
                               top_p=1.0, top_k=0, max_new_tokens=a.max_new, pad_token_id=tok.pad_token_id,
                               eos_token_id=list(stops))
        for i, qq in enumerate(batch):
            new = g[i, n:].tolist()
            end = next((k for k, t in enumerate(new) if t in stops), None)
            new = new[:end] if end is not None else new
            fh.write(json.dumps(dict(qid=qq["id"], text=tok.decode(new, skip_special_tokens=True), n_out=len(new),
                                     capped=end is None)) + "\n")
        fh.flush()
        print(f"  solve {a.tag}: {min(b0 + a.batch, len(todo))}/{len(todo)}", flush=True)
        a.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["pair", "solve", "diagnose", "extra", "extra_direct", "sweep"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--items", default="")
    ap.add_argument("--qfile", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--force", action="store_true", help="continue past the gap check (smoke tests)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--max-new", type=int, default=8192)
    ap.add_argument("--n-push", type=int, default=200)
    ap.add_argument("--capture-only", action="store_true")
    ap.add_argument("--rule", default="v1", choices=["v1", "v2"])
    ap.add_argument("--extra-items", default="")
    ap.add_argument("--layer", type=int, default=0)
    ap.add_argument("--n-layers", type=int, default=32)
    ap.add_argument("--prefix", default="extra", help="extra: output file prefix (sm2extra for the second answering model)")
    ap.add_argument("--with-proj", action="store_true", help="extra: also record the unedited position along the direction")
    a = ap.parse_args()
    a.commit = lambda: None
    {"pair": run_pair, "solve": solve, "diagnose": diagnose, "extra": extra, "extra_direct": extra_direct, "sweep": sweep}[a.phase](a)


if __name__ == "__main__":
    main()
