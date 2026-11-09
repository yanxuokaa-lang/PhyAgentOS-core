# Slurm usage

Install dependencies before submission; launchers use `--no-sync` and expect `uv`
on PATH (or set `UV_BIN` to its absolute path). From the repository root:

```bash
uv sync --locked
uv run litjev-mmlu --prepare-only --limit 10 --output mmlu-request-preview.json
mkdir -p results
export LITJEV_MODEL=/path/to/qwen-checkpoint
sbatch --partition=YOUR_PARTITION --account=YOUR_ACCOUNT scripts/benchmark.sbatch
sbatch --partition=YOUR_PARTITION --account=YOUR_ACCOUNT scripts/sequential.sbatch
```

Each benchmark requests one GPU, 8 CPUs and 128 GB RAM for 30 minutes. Do not assume
both jobs fit alongside a running 27B server. Parallel mode uses two forwards for
ten questions; sequential mode makes ten separate one-question calls, two forwards
each.

`results/job-JOBID.json` records load time, a cold run and three warm runs, accuracy,
forward counts/shapes, peak GPU allocation, and input audits. CUDA is synchronized
for timing; queueing, installation, and Python startup are excluded. Repeats reuse
the same questions. Results contain local paths/input text; review before publishing.

Serve the UI/API for up to one hour:

```bash
mkdir -p results
export LITJEV_MODEL=/path/to/qwen-checkpoint
sbatch --partition=YOUR_PARTITION --account=YOUR_ACCOUNT scripts/serve.sbatch
```

Find the compute node with `squeue`. Forward its loopback port from your workstation
(replace the placeholders):

```bash
ssh -N -J USER@LOGIN_HOST -L 8800:127.0.0.1:8800 USER@COMPUTE_NODE
```

Open http://127.0.0.1:8800/. No private host, username, account, or checkpoint path
belongs in committed scripts.
