# Steering at position A — llama3.1-8b

Share of candidates the judge accepts (verdict at A says CORRECT) when its hidden state at one layer is pushed by alpha standard deviations along a direction. alpha = 0 is the unsteered judge.

## agreement direction (layer 15)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 110 | 0.47 | 0.58 | 0.65 | 0.69 | 0.73 |
| wrong, own answer differs | 648 | 0.42 | 0.53 | 0.62 | 0.66 | 0.69 |
| correct | 150 | 0.44 | 0.51 | 0.57 | 0.65 | 0.67 |

At α=-8: wrong-and-matching accept rate changes by -0.18, wrong-and-differing by -0.20, correct by -0.13.

## correctness direction (layer 21)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 110 | 0.00 | 0.29 | 0.65 | 0.84 | 0.96 |
| wrong, own answer differs | 648 | 0.00 | 0.27 | 0.62 | 0.81 | 0.96 |
| correct | 150 | 0.00 | 0.31 | 0.57 | 0.87 | 0.99 |

At α=-8: wrong-and-matching accept rate changes by -0.65, wrong-and-differing by -0.62, correct by -0.57.

## random direction (layer 21)

| Candidates | n | α=-8 | α=-4 | α=+0 | α=+4 | α=+8 |
|---|---|---|---|---|---|---|
| wrong, own answer matches | 110 | 0.68 | 0.69 | 0.65 | 0.58 | 0.54 |
| wrong, own answer differs | 648 | 0.67 | 0.66 | 0.62 | 0.55 | 0.48 |
| correct | 150 | 0.67 | 0.68 | 0.57 | 0.55 | 0.49 |

At α=-8: wrong-and-matching accept rate changes by +0.03, wrong-and-differing by +0.06, correct by +0.11.

