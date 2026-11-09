# Jev for Hermes

`hermes-plugin-jev` connects Hermes Agent to Jev, TypeSafe AI's System One decision model, for a small set of structured judgments about each turn. Hermes keeps planning, calling tools, running its own guardrails, and asking humans for approval. Jev only adds signals.

**0.1.0 preview/beta — start in shadow mode.** Risk enforcement, verification, and tool shaping are experimental. The repository is currently private; installation requires authenticated GitHub access.

Enabling this plugin sends bounded user text and selected tool arguments to TypeSafe's hosted API. Read [PRIVACY.md](PRIVACY.md) before you enable it. Plugin code is [MIT](LICENSE); the SDK and hosted service have [separate terms](THIRD_PARTY.md).

## What it does

- Classifies each user turn (intent, complexity, side-effect likelihood, capability needs) and caches the result per session and turn.
- Proposes extra human approvals for tool calls that Jev rates as risky, uncertain, or based on incomplete input. In enforce mode this becomes a Hermes approval request.
- Flags coding completion claims that conflict with observed test, lint, or build output and can ask Hermes for one more iteration (opt-in).
- Narrows the tool list for the first provider request of a verified fresh greeting (opt-in).

## What it does not do

- It does not route providers or replace the agent model. `decision_model` selects only the Jev model.
- It cannot grant permission. `approve` in this plugin means "request a human approval"; it never returns `allow`, edits arguments, or runs a tool.
- It does not predict workflows or remove tools for anything beyond the narrow greeting case.
- Native Hermes blocks take precedence. Jev does not override, weaken, or replace them.
- It promises no token savings and no safety guarantee. Jev outputs are probabilistic signals, not authorization.

The default `mode: shadow` computes decisions and logs metadata but changes nothing in Hermes. Shadow still calls the API for every enabled stage, adds latency, and can cost money.

## Requirements

- Python 3.11+.
- The official `typesafe-sdk>=0.6.0,<0.7`.
- A Hermes build exposing the plugin contracts this plugin registers against (`register_hook`, `register_middleware`, `get_config`, `iter_hook_callbacks`, and the hooks in `plugin.yaml`). Not every Hermes version qualifies; [docs/reference.md](docs/reference.md) lists the tested commits.
- A `TYPESAFE_API_KEY` from [TypeSafe AI](https://typesafe.ai).

No Hermes core changes or patches are needed.

## Quickstart

### 1. Install, disabled, at the pinned commit

The reviewed preview runtime is available from `main`. Install the immutable runtime commit below. `hermes plugins install --ref` requires a full 40-character SHA, not a branch name:

```bash
hermes plugins install robbyczgw-cla/hermes-plugin-jev \
  --ref 7a2044364dbe502993400996f640e067196615fb --no-enable
```

The distribution and plugin manifest both use `0.1.0`; the maturity label is preview/beta, not a stable-release claim. Keep the commit pin for reproducible installs. The current `main` may contain later documentation changes without changing this runtime.

Hermes can flag this non-catalog plugin as `CAUTION` and block unattended installation. Review the named files before proceeding; this preview includes synthetic credential-redaction fixtures, SDK/API access, and subprocess-based test runners. A scanner finding is not permission to ignore the scan, and `--no-enable` does not bypass it. Do not disable scanning to make installation pass.

Recent Hermes builds install the declared SDK automatically. Older builds, or installs with `--no-deps`, need it installed into the interpreter that runs Hermes:

```bash
python -m pip install 'typesafe-sdk>=0.6.0,<0.7'
```

A missing SDK leaves the plugin inactive; Hermes keeps working.

### 2. Configure the key

Store `TYPESAFE_API_KEY` in your secret manager or in Hermes's protected environment file (`~/.hermes/.env`, mode `0600`). Never pass the key as a command-line argument or paste a literal key into scripts, issues, or configs.

### 3. Merge the safe config

Merge this into your existing Hermes `config.yaml`. `plugins.enabled` is a list; add `jev-router` to it without removing other entries. Settings live under `plugins.entries.jev-router.settings`; there is no separate config file.

```yaml
plugins:
  enabled:
    - jev-router
  entries:
    jev-router:
      settings:
        mode: shadow
        risk_gate:
          enabled: true
          block_unbindable: false
        verify:
          enabled: false
        tool_shaping:
          enabled: false
```

[examples/config.shadow.yaml](examples/config.shadow.yaml) shows the same snippet with every default filled in.

### 4. Enable and start a new process

```bash
hermes plugins enable jev-router
```

Then start a new Hermes process. For a gateway, use your normal controlled restart; do not restart it from inside an active turn. Check the result:

```bash
hermes jev status
```

This prints effective settings, whether a key is present (never its value), active state, and process-local telemetry. A fresh CLI process cannot read the in-memory counters of a running gateway.

To disable Jev for future processes:

```bash
hermes plugins disable jev-router
```

Then start a new Hermes process, or use a controlled gateway restart. Already running processes keep their loaded plugin until they exit.

Names: plugin ID `jev-router`, Python package `jev_router`, distribution `hermes-plugin-jev`. The SDK and environment variable keep their TypeSafe names.

For a bounded trial without changing your existing profile, follow the [shadow-trial checklist](docs/shadow-trial.md). It separates live API checks from synthetic guard tests and records abstentions as well as signals.

## Configuration and rollout

Roll out in this order and watch telemetry between steps:

1. **Shadow.** Keep `mode: shadow`. Enabled stages log decisions (`would_approve`, `would_nudge`, `would_shape`); none reach Hermes. Verification and shaping stay off unless you enable their flags, so to observe them in shadow, set `verify.enabled: true` or `tool_shaping.enabled: true` while keeping `mode: shadow`.
2. **Risk only.** Set `mode: enforce` with `risk_gate.enabled: true` and both `verify.enabled` and `tool_shaping.enabled` false. Hermes now shows Jev's approval requests to attended users.
3. **Optional verification.** Enable `verify` after checking nudge rates in shadow.
4. **Shaping last.** Enable `tool_shaping` only after shadow shows no false tool removals on your workloads.

`mode` accepts only `shadow` or `enforce`. Invalid values for validated settings disable the plugin and log a warning. Risk enforcement, verification, and shaping are experimental opt-ins, not an authorization boundary.

All knobs (`decision_model`, timeouts, thresholds, cache sizes, `risk_gate.read_only_tools`, telemetry limits, valid ranges) are documented in [docs/reference.md](docs/reference.md). The model key is `decision_model`; the bare `model` key belongs to Hermes and is not read here.

## Failure behavior and boundaries

- **Missing key or SDK:** plugin inactive, Hermes unchanged.
- **Timeouts, malformed responses, exhausted workers, low confidence:** Jev abstains. SDK retries are off; a late answer is never applied.
- **Exception:** in attended enforce mode, incomplete or ambiguous risk input (a follow-up such as "run the tests too", or truncated fields) still requests human confirmation even when the API call fails. Not every failure is behavior-neutral.
- **Long input:** ordinary state fields are cut at 1,800 characters (other limits also apply; this is not the whole prompt or context budget). Cut fields mark input incomplete, which in attended enforce mode can trigger repeated one-off approvals. Truncated tool output or final responses suppress verification nudges instead.
- **Unbindable arguments:** when canonical serialized arguments exceed 65,536 characters, Jev abstains by default and native policy applies. `risk_gate.block_unbindable: true` denies such calls; it never approves them.
- **Unattended contexts:** cron, `-q` single queries, API-server and webhook sessions, and bare scripts never receive Jev approval requests. Configured read-only tools skip risk assessment. Classification can still run in these contexts.
- **Hook ordering:** Hermes applies the first `block` or `approve`. Jev emits approvals only when its `pre_tool_call` hook is last in the callback snapshot; any other or unknown ordering suppresses them. See [docs/reference.md](docs/reference.md) for approval ordering.

Telemetry holds bounded metadata: decision categories, latency, model ID, token usage, completeness flags. It never stores prompts, arguments, tool output, or exception text. The sanitizer strips the configured key, credential-shaped strings, private keys, and URL credentials before truncation, but this is best-effort minimization, not permission to upload confidential data.

## Testing

After cloning at the pinned commit:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check .
ruff format --check .
python scripts/evaluate.py --output /tmp/jev-eval.json
```

Unit tests use a fake decision engine; SDK contract tests use the real SDK with a fake HTTP transport. No ordinary test needs an API key. `scripts/evaluate.py` compares disabled, shadow, risk-only, and enforce profiles on synthetic cases and reports false removals, missed or unnecessary approvals, and lost native blocks. It checks plugin guards, not Jev accuracy.

The dedicated CI job runs the Hermes contract tests against a pinned Hermes checkout and fails on any skipped or failed contract. Local runs may skip those tests when no checkout is supplied. Commands for the contract suite, the catalog validator, and upstream tests are in [docs/reference.md](docs/reference.md).

An optional live smoke test exists for people with a key in the environment:

```bash
jev-router demo
```

It classifies synthetic examples and rates a hypothetical destructive command. It never executes tools, it charges your account, and it is not a benchmark. There is no calibrated accuracy or latency benchmark for this plugin; collect shadow observations on your own workloads before trusting enforce mode.

## Links

- [docs/reference.md](docs/reference.md): implementation details, every configuration knob, decision internals, approval ordering, full test procedures.
- [PRIVACY.md](PRIVACY.md): what leaves the process, redaction bounds, provider policy.
- [THIRD_PARTY.md](THIRD_PARTY.md): SDK license and hosted-service terms.
- [SECURITY.md](SECURITY.md): reporting vulnerabilities.
- [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).
- [LICENSE](LICENSE): MIT.
