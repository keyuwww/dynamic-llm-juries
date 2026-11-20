# Direction-paper revision: cost ledger (caps set by the user 2026-11-18: Tinker <= $1,000, Modal <= $100; Cannon free)

| Time | Provider | Job | Reserved (worst case) | Actual / estimate | Running total (Modal / Tinker) |
|---|---|---|---|---|---|
| 2026-11-18 | Modal (ingridchien) | authorship controls smoke, 1 pair, CPU 8c/64GB | $1 | | |
| 2026-11-18 | Modal (ingridchien+keyuwww) | authorship controls, all pairs, CPU | $5 | | |
| 2026-11-18 | Modal (ingridchien) | smoke: outer (1 pair, 20 push, 20 test) + cot_exact Mistral 20 rows, 2 x H100 <= 30 min | $4 | | |
| 2026-11-18 | Modal (ingridchien) | smoke runs done (2 attempts; the first waited for H100) | | ~$3 est. | ~$4 / $0 |
| 2026-11-18 | Modal (ingridchien) | outer evaluation, 11 pairs, H100/A100, <= 1 h each | $45 | | |
| 2026-11-18 | Modal (ingridchien) | Mistral-7B reasoning rerun with exact score (MMLU main; MATH main, sm, sm2), <= 1.5 h | $6 | | |
| 2026-11-18 | Modal (keyuwww) | outer evaluation, Llama-3.1-8B MATH (legacy storage), <= 1 h | $4 | | |
| 2026-11-19 | Modal (ingridchien) | exact-score parity check, Mistral-7B MATH, 20 rows (max vLLM vs HF difference 0.31 nats, bf16) | $1 | | |
| 2026-11-19 | Modal billing report | all of the above, actual: ingridchien $25.5 (outer + Mistral rerun app $24.2), keyuwww $2.2 | | **~$28** | **~$28 / $0** |

Cannon was not used. Tinker was not used.
| 2026-11-20 | Modal (ingridchien + keyuwww) | nested surface residualization, 19 pairs, CPU, run twice (second adds the scale-matched variant) | $5 | ~$0.06 (billing report) | ~$28 / $0 |
