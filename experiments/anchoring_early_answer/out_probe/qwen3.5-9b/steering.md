# Steering at position A — qwen3.5-9b

Share of candidates the judge accepts (verdict at A says CORRECT) when its hidden state at one layer is pushed by alpha standard deviations along a direction. alpha = 0 is the unsteered judge.

## agreement direction (layer 19)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 126 | 0.37 | 0.42 | 0.45 | 0.49 | 0.50 |
| wrong, own answer differs | 634 | 0.20 | 0.23 | 0.26 | 0.28 | 0.29 |
| correct | 150 | 0.38 | 0.45 | 0.48 | 0.49 | 0.50 |

At α=-8: wrong-and-matching accept rate changes by -0.08, wrong-and-differing by -0.06, correct by -0.10.

## correctness direction (layer 28)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 126 | 0.00 | 0.10 | 0.45 | 0.78 | 0.98 |
| wrong, own answer differs | 634 | 0.00 | 0.03 | 0.26 | 0.54 | 0.84 |
| correct | 150 | 0.00 | 0.08 | 0.48 | 0.87 | 0.97 |

At α=-8: wrong-and-matching accept rate changes by -0.45, wrong-and-differing by -0.26, correct by -0.48.

## random direction (layer 28)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 126 | 0.49 | 0.46 | 0.45 | 0.48 | 0.54 |
| wrong, own answer differs | 634 | 0.29 | 0.27 | 0.26 | 0.28 | 0.30 |
| correct | 150 | 0.51 | 0.49 | 0.48 | 0.51 | 0.53 |

At α=-8: wrong-and-matching accept rate changes by +0.04, wrong-and-differing by +0.02, correct by +0.03.

