"""Per-pair points behind the calibration chart: the best judge's stated confidence vs whether it was wrong.

No binning: one row per pair. Two conditions, as in roc_curves.py:
  all         every pair; wrong = wrong in at least one order (stored run); own_flip marks pairs it flips
  consistent  pairs where the best judge is consistent; wrong = wrong in both orders
conf = the best judge's stated confidence from the confidence run, mean of both orders.
Usage: python calibration_points.py -> results/flips/calibration_points.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conf_analysis import per_pair, read  # noqa: E402
from flip_analysis import load  # noqa: E402

BENCHES = ["bffpair", "judgebench", "alpacafarm", "mtbhuman"]


def main():
    out = {}
    for b in BENCHES:
        df, target, J = load(b)
        P = per_pair(read("confidence", b))
        c = P[P.judge == target].set_index("pair_id").stated
        d = df.join(c.rename("conf"), how="inner").dropna(subset=["conf"])
        allp = [[round(float(r.conf), 1), int(r.t_conf_err == 1 or r.t_flip == 1), int(r.t_flip)] for r in d.itertuples()]
        cons = [[round(float(r.conf), 1), int(r.t_conf_err)] for r in d[d.t_flip == 0].itertuples()]
        out[b] = dict(target=target, all=allp, consistent=cons)
        print(b, target, len(allp), sum(x[1] for x in allp), len(cons), sum(x[1] for x in cons))
    (HERE / "results" / "flips" / "calibration_points.json").write_text(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
