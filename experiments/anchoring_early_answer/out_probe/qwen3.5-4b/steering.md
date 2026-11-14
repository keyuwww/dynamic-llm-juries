# Steering at position A — qwen3.5-4b

Share of candidates the judge accepts (verdict at A says CORRECT) when its hidden state at one layer is pushed by alpha standard deviations along a direction. alpha = 0 is the unsteered judge.

## agreement direction (layer 16)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 128 | 0.30 | 0.38 | 0.40 | 0.38 | 0.35 |
| wrong, own answer differs | 626 | 0.15 | 0.22 | 0.24 | 0.24 | 0.24 |
| correct | 150 | 0.27 | 0.43 | 0.45 | 0.44 | 0.42 |

At α=-8: wrong-and-matching accept rate changes by -0.10, wrong-and-differing by -0.10, correct by -0.19.

## correctness direction (layer 25)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 128 | 0.00 | 0.01 | 0.40 | 0.77 | 0.93 |
| wrong, own answer differs | 626 | 0.00 | 0.00 | 0.24 | 0.62 | 0.92 |
| correct | 150 | 0.00 | 0.01 | 0.45 | 0.79 | 0.97 |

At α=-8: wrong-and-matching accept rate changes by -0.40, wrong-and-differing by -0.24, correct by -0.45.

## random direction (layer 25)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 128 | 0.31 | 0.35 | 0.40 | 0.48 | 0.62 |
| wrong, own answer differs | 626 | 0.19 | 0.21 | 0.24 | 0.28 | 0.37 |
| correct | 150 | 0.38 | 0.42 | 0.45 | 0.49 | 0.57 |

At α=-8: wrong-and-matching accept rate changes by -0.09, wrong-and-differing by -0.05, correct by -0.07.

