# System 1 Intent Routing Probes

Standalone capability validation for local Laya, remote Jev, and `gpt-6-luna`
Decisions intent/route choices. The probes share one fixed dataset and scorer labels.
They record predictions only and do not import PAOS, read live task state, call handlers,
or change an existing route.

## Local validation

```bash
PYTHONPATH=research/decision-api-intent-probe \
  python -m decision_intent_probe validate \
  --config research/decision-api-intent-probe/config.json
```

Build requests without network access:

```bash
PYTHONPATH=research/decision-api-intent-probe \
  python -m decision_intent_probe run \
  --config research/decision-api-intent-probe/config.json \
  --phase development --dry-run
```

## API run

The runner uses `https://api.shuaiapi.com/v1/decisions` by default. Set the key only in
the process environment; it is never written to config or artifacts.

```bash
export DECISIONS_API_KEY='...'
export DECISIONS_API_URL='https://api.shuaiapi.com/'
PYTHONPATH=research/decision-api-intent-probe \
  python -m decision_intent_probe run \
  --config research/decision-api-intent-probe/config.json \
  --phase development --smoke
```

The first run is five development smoke cases. Re-run the same directory with
`--resume <run-dir> --phase development` to complete the remaining development cases,
then run evaluation. The output directory is unique under `out/decision-api-intent-probe/`.
Valid responses are not repeated by resume.

Offline scoring reports hard-label accuracy plus per-question probability coverage,
10-bin ECE, multiclass Brier score, and NLL. Probability metrics are computed only for
valid responses carrying the complete candidate distribution; transport failures remain
visible through answer coverage and are not silently included as probability predictions.

## Local Laya run

Use a dedicated interpreter and an out-of-repository Hugging Face cache. The three
published checkpoints are tested independently because they target different language
and workflow distributions.

```bash
export HF_HOME=/home/yanxu/laya-system1/huggingface
export HF_HUB_OFFLINE=1
export USE_TF=0
export TMPDIR=/home/yanxu/laya-system1/tmp
mkdir -p "$TMPDIR"

for checkpoint in english multilingual typed-decisions; do
  PYTHONPATH=research/decision-api-intent-probe \
    /home/yanxu/laya-system1/.venv/bin/python -m laya_intent_probe run \
    --config research/decision-api-intent-probe/laya_config.json \
    --checkpoint "$checkpoint" --phase development --smoke
done
```

The English and typed-decisions checkpoints are included for controlled comparison;
their result on this Chinese dataset is not evidence of general multilingual quality.

## Remote Jev run

Set the key in the environment only. The config stores the IDNA ASCII form of the
authorized endpoint host; the Unicode and ASCII hostnames resolve to the same endpoint.

```bash
export JEV_API_KEY='...'
PYTHONPATH=research/decision-api-intent-probe \
  python -m jev_intent_probe run \
  --config research/decision-api-intent-probe/jev_config.json \
  --phase development --smoke
```

Interrupted Jev runs can be resumed without repeating terminal predictions:

```bash
PYTHONPATH=research/decision-api-intent-probe \
  python -m jev_intent_probe run \
  --config research/decision-api-intent-probe/jev_config.json \
  --phase development --resume out/jev-intent-probe/<run-id>
```

## Scope

The dataset is synthetic Chinese text, 20 development and 60 evaluation cases. Route values
are labels only. A successful report is evidence for the next shadow-validation design, not
permission to replace PAOS routing.
