"""Role construction, adapted from Appendix A.2 of Stopping and Routing LLM Judge Panels."""


def construct_panel(judges, gain_fn, slice_gain_fn, cost, slices, tau_P=0.005, tau_f=0.005, lam=0.0):
    """
    gain_fn(j, S)           -> g(j|S), using the construction-fit/validation split
    slice_gain_fn(j, S, f)  -> A_f(j|S) for slice name f
    cost[j]                 -> $/call
    slices                  -> names of the slices allowed this repeat (after prevalence / size gating)
    Returns: S (global panel, role=Complement),
             specialists (dict slice -> judges routed only on that slice),
             copies (judges dropped as redundant)
    """
    S, specialists, copies = [], {f: [] for f in slices}, []
    unassigned = list(judges)

    while unassigned:
        # 1. try to grow the global panel
        scored = [(j, gain_fn(j, S) - lam * cost[j]) for j in unassigned]
        j_best, best_val = max(scored, key=lambda t: t[1])
        if best_val > tau_P:
            S.append(j_best)
            unassigned.remove(j_best)
            continue  # re-score everyone against the new, larger S

        # 2. nobody clears the global bar -> every remaining judge gets one pass over the slices
        #    and leaves `unassigned` either way, so the while-loop exits on its own
        for j in list(unassigned):
            slice_scores = [(f, slice_gain_fn(j, S, f) - lam * cost[j]) for f in slices]
            f_best, sval = max(slice_scores, key=lambda t: t[1]) if slice_scores else (None, float("-inf"))
            if sval > tau_f:
                specialists[f_best].append(j)
            else:
                copies.append(j)
            unassigned.remove(j)
    return S, specialists, copies
