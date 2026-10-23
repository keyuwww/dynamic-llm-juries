# AlpacaFarm: flip signal by human vote margin

4 crowd votes per pair. Best judge deepseek-v3.1; consistent pairs only.

| votes         |   pairs |   conf_err_rate |   auroc_flips |   auroc_disagree |   auroc_pooled |   mean_flips |
|:--------------|--------:|----------------:|--------------:|-----------------:|---------------:|-------------:|
| unanimous 4-0 |     162 |           0.13  |         0.757 |            0.686 |          0.811 |        1.167 |
| 3-1           |     219 |           0.265 |         0.607 |            0.573 |          0.621 |        1.658 |
