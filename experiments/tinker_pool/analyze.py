"""
Summaries shared by the Tinker pool scripts.

- headroom(): per-model accuracy, best single model, oracle, and how often each model is the ONLY one
  that gets an item right. This is the "is there anything for a router to gain?" check.
- cost_table(): measured tokens and $ per call per model (from cached rows).
"""
import statistics
from collections import defaultdict

from common import POOL_BY_KEY, call_cost, fmt


def headroom(matrix, models, title):
    """matrix: {item_id: {model_key: 0/1}}. Only items where every listed model has a label are used,
    so all strategies share one denominator."""
    items = [i for i, row in matrix.items() if all(m in row for m in models)]
    L = [f"## {title}", ""]
    if not items:
        return L + ["(no items with labels for every model yet)", ""], {}
    acc = {m: sum(matrix[i][m] for i in items) / len(items) for m in models}
    best = max(acc, key=acc.get)
    oracle = sum(max(matrix[i][m] for m in models) for i in items) / len(items)
    none_right = sum(1 for i in items if max(matrix[i][m] for m in models) == 0) / len(items)
    unique = {m: sum(1 for i in items if matrix[i][m] == 1 and sum(matrix[i][x] for x in models) == 1)
              for m in models}
    best_wrong_other_right = sum(1 for i in items if matrix[i][best] == 0 and max(matrix[i][m] for m in models) == 1)
    L += [f"Items scored by every model: {len(items)}", "",
          "| Model | Tier | Accuracy | Only model correct (# items) |", "|---|---|---|---|"]
    for m in sorted(models, key=lambda m: -acc[m]):
        L.append(f"| {m} | {POOL_BY_KEY[m]['tier']} | {fmt(acc[m])} | {unique[m]} |")
    L += ["", "| Headroom check | |", "|---|---|",
          f"| Best single model | **{best}** ({fmt(acc[best])}) |",
          f"| Oracle (any model correct) | {fmt(oracle)} |",
          f"| **Oracle − best single** (room a router can win) | **{fmt(oracle - acc[best])}** |",
          f"| Items the best model misses but another gets right | {best_wrong_other_right} ({fmt(best_wrong_other_right / len(items))}) |",
          f"| Items no model gets right | {fmt(none_right)} |", "",
          "Rule of thumb from the plan: keep a model in the routing pool if no single model wins almost "
          "everywhere and oracle − best is ≥ ~0.08 (BFF-Bench's original six models gave only ~0.04).", ""]
    return L, dict(n=len(items), acc=acc, best=best, oracle=oracle, gap=oracle - acc[best], none_right=none_right)


def cost_table(rows, title="Measured tokens and cost"):
    """rows: dicts with model, n_in, n_out (one per API call)."""
    by = defaultdict(list)
    for r in rows:
        by[r["model"]].append(r)
    L = [f"## {title}", "", "| Model | Calls | Avg input tok | Avg output tok | $ / call | Total $ |",
         "|---|---|---|---|---|---|"]
    total = 0.0
    per_call = {}
    for m, rs in sorted(by.items()):
        spec = POOL_BY_KEY[m]
        cost = sum(call_cost(spec, r.get("n_in"), r.get("n_out")) for r in rs)
        total += cost
        per_call[m] = cost / len(rs)
        L.append(f"| {m} | {len(rs)} | {statistics.mean(r.get('n_in') or 0 for r in rs):,.0f} | "
                 f"{statistics.mean(r.get('n_out') or 0 for r in rs):,.0f} | ${per_call[m]:.5f} | ${cost:.3f} |")
    L += ["", f"**Total: ${total:.2f}** (Tinker list prices; cached-prefill discounts not counted, so this is an upper bound)", ""]
    return L, per_call
