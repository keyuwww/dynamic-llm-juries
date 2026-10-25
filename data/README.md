# Data

| Path | What it is | Source |
|---|---|---|
| [verdicts.parquet](verdicts.parquet) | Three expert votes per answer: correct, incorrect or not sure. The notebook keeps the BFF-Bench rows | [kensho/VERDICTS](https://huggingface.co/datasets/kensho/VERDICTS) on Hugging Face, Apache-2.0 |
| [bffbench.parquet](bffbench.parquet) | BFF-Bench's finance questions, with one expert reference per question turn | [kensho/BFFBench](https://huggingface.co/datasets/kensho/BFFBench) on Hugging Face, Apache-2.0 |
| [gpt_oss_120b_rejections_read.csv](gpt_oss_120b_rejections_read.csv) | A hand reading, on Oct 16, 2026, of the 23 correct answers gpt-oss-120b rejected with the experts' rules but accepted on the standard prompt. Each row has one reason, and whether its reasoning says the reference looks wrong | Ours |

Both Kensho datasets are released under the Apache License 2.0 and are copied here unchanged. The experts' rules in [prompts/experts_rules.md](../prompts/experts_rules.md) are the annotator guidelines in appendix A.4 of Kensho's paper, No Free Labels ([arXiv 2503.05061](https://arxiv.org/abs/2503.05061)).
