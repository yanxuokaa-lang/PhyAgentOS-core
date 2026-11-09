# Hermes-Jev

**An asynchronous Jev decision nervous system for Hermes Agent.**

Hermes remains the reasoning and execution engine. Jev supervises accountable decisions in parallel: turn admission, adaptive local relevance routing, bounded decision comparison, completion/recovery control, and high-confidence challenge delivery. The design is explicitly optimized around the observed ~500 ms-class remote decision latency: ordinary Hermes execution does not wait for Jev.

> Community project. Not affiliated with or endorsed by TypeSafe AI or Nous Research.

## v0.2.1.2

Stabilization patch for the automatic Jev ContextEngine:

- bound automatic semantic curation to at most 48 recoverable raw evidence items per boundary, oldest first;
- keep deferred evidence untouched and skip existing `JEV_CONTEXT_ANCHOR` results so compaction progresses instead of nesting anchors;
- make Jev curation and Hermes built-in fallback failures fully fail-open to the original message list;
- make shadow curation failures and selection pressure observable in ContextEngine status;
- count shadow ANCHOR/DROP actions as proposals only, not completed compaction;
- avoid remote semantic calls for deterministically unrecoverable evidence in the automatic engine path.

The direct TypeSafe System One transport now also has independent live-account interoperability evidence from v0.2.1.1 issue #1. That validates the released v0.2.1.1 transport path; this v0.2.1.2 package does not claim a new credentialed live run unless one is performed against the candidate.

See [`docs/BUGFIX_0.2.1.2.md`](docs/BUGFIX_0.2.1.2.md).

## v0.2.1.1

Patch release for three live Muna integration defects found against 0.2.1:

- `jev_assess` now advertises the same typed choice/score requirements enforced by runtime validation, so deferred-tool models can construct valid calls from schema alone.
- `jev_*` tool outcomes are an explicit nervous-system self-observation boundary: they are logged locally but cannot recursively create background Jev assessments.
- explicit remote decision tools now return receipt-backed provenance (`receipt_id`, `provenance_status`, provider/model/transport, subject hash, and result hash) so a user-visible Jev claim can be audited one-to-one.

See [`docs/BUGFIX_0.2.1.1.md`](docs/BUGFIX_0.2.1.1.md) for the bug-to-fix matrix and verification boundary.

## v0.2.1

Public tools: the seven v0.1.5.5 tools plus `jev_nervous_event`. Public hook names: `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `transform_tool_result`, `pre_verify`, `post_llm_call`, and `on_session_end`.

The recommended path is the nervous system, not synchronous evaluate-every-tool gating. At turn ingress a background Jev admission call classifies the turn as `OFF`, `WATCH`, or `ON`; Hermes starts immediately. During supervised turns a local adaptive router consumes structured events, suppresses routine/redundant state, batches in-flight bursts, and sends only decision-significant state to Jev. Agreement and low-confidence disagreement remain silent telemetry. High-confidence disagreement is delivered only while the challenged state is current.

v0.2.1 hardens the recovery/control path discovered during Muna testing: identical failure episodes are fingerprinted locally, repeated equivalent failures stop generating provider calls, and a third identical failure creates a provider-independent `REPLAN` lease. In `correct_next`/`precommit`, the composed pre-tool control seam prevents the exact failed action from executing again unless Jev explicitly chose `RETRY`. Decision IDs now connect the decision, delivery, next action, disposition, and outcome telemetry. `jev_stats` is compact by default to avoid feeding tens of kilobytes of telemetry back into the main model context.

See:

- [`docs/NERVOUS_SYSTEM.md`](docs/NERVOUS_SYSTEM.md)
- [`docs/GUIDE.md`](docs/GUIDE.md)
- [`docs/SETUP.md`](docs/SETUP.md)
- [`docs/PROVIDER_SETUP.md`](docs/PROVIDER_SETUP.md)
- [`VERIFICATION.md`](VERIFICATION.md)

Both OpenRouter Decisions and direct TypeSafe System One are supported. Only the selected provider credential is required.

## Historical v0.1.5.5 documentation

### v0.1.5.5

The release moves context management from "save tokens" to **preserve the smallest sufficient working set for correct continuation**.

Public tools:

- `jev_decide` — one bounded choice plus calibrated probabilities.
- `jev_rank` — rank a bounded candidate set from Jev probabilities.
- `jev_verify` — `PASS | RETRY | REPLAN | ESCALATE` verification.
- `jev_assess` — up to 16 native `noul`, `choice`, or `score` questions over one shared state.
- `jev_context_curate` — semantic context-value planning with deterministic retention policy.
- `jev_context_rehydrate` — restore sanitized evidence from a local evidence anchor; no provider call.
- `jev_stats` — local active-profile receipt + context telemetry; no provider call.

Hooks:

- `pre_tool_call` — optional `off | advisory | enforce` Jev gate.
- `post_tool_call` — privacy-minimized evidence observation for context telemetry/rehydration.

Optional context engine:

- `context.engine: jev` — Jev-first context management using Hermes' public `ContextEngine` interface.
- Never auto-activated. The built-in Hermes compressor remains the default until explicitly selected.
- If Jev cannot safely reclaim eligible tool evidence, the engine can fall back to Hermes' built-in `ContextCompressor` rather than stall on text-heavy sessions.

## The context governor

Jev does **not** decide deletion directly. For each eligible evidence unit it estimates four semantic quantities:

- `needed_again` — probability the evidence will matter later in the current goal.
- `exact_required` — probability exact original detail will be needed rather than provenance/identity.
- `superseded` — probability newer state has made the evidence stale or redundant.
- `conflict` — probability it participates in an unresolved contradiction.

Local deterministic code then chooses an action:

- `KEEP_EXACT` — retain original content.
- `PIN` — keep exact while a lifecycle lease is active or conflict is unresolved.
- `ANCHOR` — replace bulk content with deterministic provenance, hash, prefix, and recovery pointer.
- `DROP` — allowed only for deterministically recoverable, low-value, superseded evidence in explicit curation.
- `REHYDRATE` — restore sanitized anchored evidence from the local ledger.

Automatic ContextEngine mode never physically removes a tool-result message because doing so can orphan its corresponding assistant tool call. A proposed `DROP` becomes a minimal anchor instead.

### Lifecycle leases

User/assistant text is protected. Nonrecoverable failure evidence is automatically leased `until_verification_pass`; a real `jev_verify` `PASS` releases that lease for later curation. Callers can also provide an explicit `metadata.lease`.

### Shadow mode

Use `mode=shadow` to collect Jev's proposed actions without changing returned evidence. Shadow plans are written to the evidence ledger and can be summarized with:

```bash
python3 scripts/context_shadow_report.py
python3 scripts/jev_report.py
```

The report includes proposed action counts, proposed character savings, rehydration counts, and recovery-demand rate. The standalone reporter is profile-aware: when launched from `~/.hermes/profiles/<name>/plugins/hermes-jev`, it infers that profile instead of silently reading the global default ledger. Recovery demand is a tuning signal, not automatically a false-forget failure.

Inside Hermes, `jev_stats` is the preferred sanity check because it reads the exact active-profile paths used by the running process.

See [`docs/CONTEXT_CURATION.md`](docs/CONTEXT_CURATION.md).

## Provenance

Every live Jev result carries an explicit execution block so a main chat model cannot be mistaken for the decision provider:

```json
{
  "execution": {
    "engine": "hermes-jev",
    "version": "0.1.5.5",
    "transport": "openrouter-decisions",
    "live_provider_call": true
  },
  "provider": "TypeSafe",
  "model": "typesafe/jev-1.13-20260917",
  "request_id": "gen-dec-..."
}
```

`jev_context_rehydrate` instead reports `transport: local-evidence-ledger` and `live_provider_call: false`. `jev_stats` reports `transport: local-telemetry`.

## Configuration

The canonical model setting is `jev_model`. `model_id` remains accepted as a migration alias for the hand-fixed 0.1.5.1 tree.

```bash
hermes config set plugins.entries.hermes-jev.settings.jev_model typesafe/jev-1.13 --force
hermes config set plugins.entries.hermes-jev.settings.timeout_seconds 15 --force
```

### Gate

```bash
hermes config set plugins.entries.hermes-jev.settings.gate_mode advisory --force
```

Modes:

- `off` — no automatic Jev gate calls.
- `advisory` — evaluate material/unknown calls and receipt them, never alter execution.
- `enforce` — high-confidence `BLOCK` can block; `APPROVAL`, low confidence, or provider failure route toward human approval.

`0.1.5.5` defaults the gate to `gate_scope=selective`. A conservative local prefilter bypasses Jev for exact known read-only Hermes tools and narrowly parsed read-only terminal commands (`pwd`, `ls`, `rg`, `git status`, `git diff`, etc.). Unknown, mutating, shell-composed, or ambiguous calls still go to Jev. This removes a network round trip from routine introspection without weakening the gate for consequential actions.

To restore the old evaluate-every-call behavior:

```bash
hermes config set plugins.entries.hermes-jev.settings.gate_scope all --force
```

`jev_stats` reports gate events separately (`bypassed`, `evaluated`, provider errors, provider latency, and estimated provider calls avoided) so the latency impact is directly measurable.

### Explicit curation

Recommended evaluation phase:

```bash
hermes config set plugins.entries.hermes-jev.settings.context_curation_mode shadow --force
```

Switch to `apply` only after reviewing your own shadow telemetry.

### Evidence ledger

Defaults:

```text
$HERMES_HOME/jev/context-ledger.jsonl
```

`context_ledger_detail=sanitized` stores force-redacted content and supports rehydration. `hash` stores no rehydratable content and is the stricter privacy mode.

### Opt-in ContextEngine

Hermes still uses its built-in compressor unless you explicitly select Jev:

```bash
hermes config set context.engine jev --force
```

Useful settings:

```bash
hermes config set plugins.entries.hermes-jev.settings.context_engine_mode shadow --force
hermes config set plugins.entries.hermes-jev.settings.context_engine_threshold_percent 0.72 --force
hermes config set plugins.entries.hermes-jev.settings.context_engine_fallback_builtin true --force
```

Both `context_curation_mode` and `context_engine_mode` default to `shadow` in 0.1.5.5. After evaluating shadow mode, use `context_engine_mode=apply` to let the engine anchor eligible old tool evidence at compaction boundaries.

Do **not** add `jev` to a saved static platform-toolset list merely to expose these tools. Hermes dynamically registers plugin tools; on current Hermes builds a saved `jev` entry may produce an early `Unknown toolsets: jev` warning before plugin discovery even though the plugin subsequently loads correctly.

## Privacy

All Jev-bound state goes through Hermes-Jev's recursive secret redaction. Decision receipts default to hash-only state. The evidence ledger is separate because rehydration requires retaining content; its `sanitized` mode force-redacts stored content and metadata.

Decision receipts:

```text
$HERMES_HOME/jev/receipts.jsonl
```

Evidence ledger:

```text
$HERMES_HOME/jev/context-ledger.jsonl
```

See [`SECURITY.md`](SECURITY.md).

## Maintainer / release status

The source of truth for a release is the versioned commit plus its GitHub Actions result. GitHub Releases may lag source history; do not infer the current plugin version from the releases page alone.

Maintainers can publish a verified release from the current default-branch version using the manual **release** GitHub Actions workflow. The workflow refuses a requested version that does not match `pyproject.toml`, reruns unit/compile/release verification, creates source archives, writes SHA-256 checksums, and creates the GitHub Release without overwriting an existing tag.

## Testing

Offline:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
```

Live synthetic regression suite:

```bash
set -a
source ~/.hermes/profiles/muna/.env
set +a
python3 scripts/live_api_suite.py
```

The live path has been validated through Hermes -> hermes-jev -> OpenRouter Decisions -> TypeSafe Jev using a free primary Hermes model. Four verified live calls consumed 2,264 input + 281 output tokens, cost $0.000095088 total, and averaged 419.276 ms provider latency. See [`docs/LIVE_TEST_NOTES_2026-09-17.md`](docs/LIVE_TEST_NOTES_2026-09-17.md). The context-governor policy remains shadow-first before automatic apply mode.

## Benchmarking objective

Raw compression ratio is not the primary metric. The target is **continuation fidelity per context token**: preserve constraints and exact failure evidence, reduce stale/recoverable clutter, avoid repeated work, and successfully rehydrate when older evidence becomes relevant again.

See [`docs/BENCHMARKING.md`](docs/BENCHMARKING.md).

## License

MIT

### v0.2.1 repeated-failure loop breaker

The local fallback threshold is configurable:

```bash
hermes config set plugins.entries.hermes-jev.settings.nervous_repeated_failure_local_replan_at 3 --force
```

The default `3` means the first equivalent failure may be assessed by Jev, later
identical failures are provider-deduplicated, and the third identical failure
activates a local `REPLAN` control even if remote supervision is late. In
`correct_next`/`precommit`, the next exact same failed action is blocked; an explicit
Jev `RETRY` permits one retry.

For debugging, `jev_stats` now defaults to a compact summary. Request a narrow section
instead of injecting the whole telemetry ledger into model context, for example:

```text
jev_stats {"section":"nervous","include_recent":true,"recent_limit":3}
```