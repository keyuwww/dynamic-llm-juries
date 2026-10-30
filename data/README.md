# Data

| Path | What it is | Source |
|---|---|---|
| [verdicts.parquet](verdicts.parquet) | Three expert votes per answer, correct, incorrect or not sure, with each answer's conversation, for the BFF-Bench and MT-Bench answers. The notebook labels each answer by the majority vote | [kensho/VERDICTS](https://huggingface.co/datasets/kensho/VERDICTS) on Hugging Face, Apache-2.0 |
| [bffbench.parquet](bffbench.parquet) | BFF-Bench's finance questions, with one expert reference per question turn | [kensho/BFFBench](https://huggingface.co/datasets/kensho/BFFBench) on Hugging Face, Apache-2.0 |
| [cmtbench.parquet](cmtbench.parquet) | Kensho's corrected MT-Bench: the 20 math and reasoning questions of MT-Bench, numbers 101 to 120, with a corrected reference per question turn | [kensho/CMTBench](https://huggingface.co/datasets/kensho/CMTBench) on Hugging Face, Apache-2.0, revision f2ddc1dd |

All three files are copied here unchanged. `items()` in [lib/self_agreement.py](../lib/self_agreement.py) builds the 544 answers from them, with fixed seeds, so the same answers come out on every run:

- **Finance answers.** Of the BFF-Bench answers in VERDICTS, the notebook keeps the ones where at least 2 of 3 experts agree, and the majority is the label. It drops one conversation, `fc9858ab`, whose record holds the turn-1 reference where the question should be. That leaves 799 answers. A seeded shuffle then takes 2 answers from each of the 158 question turns, 316 answers from 79 conversations.
- **MT-Bench answers.** The notebook keeps every VERDICTS answer to the 20 CMTBench questions where at least 2 of 3 experts agree, 228 of 240.
- **References and order.** Each answer's reference is the BFF-Bench or CMTBench reference for its question turn. No juror saw it, but the grader did when it judged the jurors' own answers. The finance answers come first in reading order, then the MT-Bench answers in a seeded order.

The expert labels, BFF-Bench and the corrected MT-Bench references are from Kensho's paper, No Free Labels: Limitations of LLM-as-a-Judge Without Human Grounding, by Krumdick, Lovering, Reddy, Ebner and Tanner ([arXiv 2503.05061](https://arxiv.org/abs/2503.05061)). Appendix A.4 of the paper gives the rules its experts labelled by. The same MT-Bench references are also in [kensho/NoFreeLabels](https://huggingface.co/datasets/kensho/NoFreeLabels), Apache-2.0, and CMTBench is used here because it is the smaller file. The MT-Bench questions come from MT-Bench (Zheng et al., [arXiv 2306.05685](https://arxiv.org/abs/2306.05685)), released in [FastChat](https://github.com/lm-sys/FastChat) under the Apache License 2.0. Every dataset here is released under the Apache License 2.0.
