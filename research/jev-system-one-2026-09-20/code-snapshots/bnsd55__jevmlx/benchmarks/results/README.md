# benchmarks/results/

One folder per bench submission, written by `jevmlx bench`:

```
<machine>-<model-slug>/          e.g. m2pro-32gb--mlx-community--qwen2.5-0.5b-instruct-4bit
  <dataset>.dataset.lock.json    provenance of each dataset the runs consumed
  SUMMARY.md                     one-glance table across all combinations
  README.md                      notes (gzip status, how to read the folder)
  <track>-<scorer>-<dataset>/    e.g. parallel-trie-bundled
    predictions.jsonl            one JSON object per field decision
    run.json                     run manifest: model, config, counts
    report.json                  metrics computed offline by jevmlx report
    report.md                    human-readable summary of report.json
```

Machine tag: `<chip-lowercase>-<ram>gb` (e.g. `m2pro-32gb`). Model slug: the
model id lowercased with `/` replaced by `--`.

To contribute a results folder from your own Apple Silicon Mac, follow
[BENCHMARKING.md](../../BENCHMARKING.md): run `jevmlx bench --model M`, commit
only this folder, and paste `SUMMARY.md` into the PR. Predictions pushing the
folder past 5 MB are gzipped automatically (`predictions.jsonl.gz`).
