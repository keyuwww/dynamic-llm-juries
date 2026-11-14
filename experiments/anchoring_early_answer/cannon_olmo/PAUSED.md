# OLMo-3 Think stages: paused on 2026-11-09 (to give Cannon GPUs to belief steering)

All three Think stages FINISHED generating (own answers + judging transcripts, 4,058 each). They are saved on Cannon:

    /n/netscratch/tambe_lab/Everyone/keyuwang/olmo_think/out/<key>/generations.jsonl
    keys: olmo3-7b-think-sft, olmo3-7b-think-dpo, olmo3-7b-think

What is NOT done: the readout step (verdict at A / 25 / 50 / 75 / E / C + hidden states at A / E / C) for all three.
It cannot resume part-way, so each stage reruns it from the start (~1-1.5 GPU-hours each).

Cancelled jobs (nothing is queued or running for OLMo):
- 59123350_0, _2  Think-SFT and final Think, cancelled ~55 min into the readout
- 59123350_1      Think-DPO, failed: out of GPU memory on an A100-80GB (one ~64K-token transcript)
- 59138242_1      Think-DPO rerun on H200, cancelled while queued
- 59139704_0, _2  resubmission of SFT / final Think on H200, cancelled while queued

To restart (use H200s: the readout of long thinking transcripts does not fit on an A100-80GB):

    cd /n/netscratch/tambe_lab/Everyone/keyuwang/olmo_think
    sbatch --array=0-2 --gres=gpu:nvidia_h200:1 --mem=160G stage.sh

stage.sh skips generation (all done) and runs the readout. Then pull out/<key>/ back to
experiments/anchoring_early_answer/out_open/<key>/, run open_ingest.py --key <key> --think, the GLM match / fill
(tinker_jobs.py --open <key>; costs Tinker money, estimate first), and open_analysis.py --key <key>.

Also not done for OLMo: GLM matching of the Instruct stages on BFF (they were matched on BBEH / RB2 / JudgeBench only).
