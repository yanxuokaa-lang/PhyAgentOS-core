# Jevra

The opt-in [focused reader and corrected decision flow](docs/focused-reader.md) use Luna to return cited answers and Jev to review managed semantic transitions. The historical [first reader pair](evals/reports/2026-09-18-reader-comparison.md) passed authored code/fact checks but did not invoke the offered helper; that non-adoption result is preserved.

The [gate preflight](evals/reports/2026-09-18-reader-gate-validation.md) passed 14 direct built-hook cases and normal scoped trust review. After correcting the preflight/parent context mismatch, a [fresh v2 task](evals/reports/2026-09-18-reader-gate-task-v2.md) observed one gate redirect and one answered Luna/Jev reader call, with passing authored quality. All components used 128,778 tokens; whole-task savings and general activation remain unproven. A small comparison under matched corrected host settings is the next evidence gate.

An open-source development plugin for Codex and Claude Code, developed from scratch with engineering memory, bounded delegated work, and TypeSafe Jev judgments as its product direction.

Users keep working in their existing agent. An opt-in `PreToolUse` hook redirects large reads to a helper: Jev selects source excerpts, and the main LLM interprets them and writes code. `code-context` selects implementation references. The original `UserPromptSubmit` skill router remains available.

**Status: executable developer alpha, `0.1.0-alpha.2`.** Large-read command hooks have run in authenticated Codex CLI and Claude Code sessions. The Jev selector has a live provider check; complete-task measurements are documented separately. This is not a general decision framework or a production release.

The adopted [decision architecture](docs/decision-architecture.md) assigns every explicit semantic decision in a Jevra-managed workflow to Jev. LLMs propose solutions and produce artifacts; code enforces policy and execution. This broader lifecycle is planned, and hooks cannot control hidden host decisions.

## What works

The [development-brain architecture](docs/development-brain.md) defines the adopted product direction. Native engineering memory and repository indexing remain planned. An opt-in managed test generator is available through MCP for configured pure-function profiles; repeated ordinary adoption and full plugin installation remain open.

- Shared TypeScript core, official TypeSafe SDK provider, CLI, and separate host adapters.
- Explicit skill directories, validated YAML metadata, content revisions, and bounded inputs.
- Disabled, observe (default), and advise modes; explicit skill mentions retain native handling.
- Choice selection plus an independent Noul check for requests requiring multiple skills.
- Deadlines, cancellation, no automatic retries, response validation, and native fallback.
- Local metadata traces, retention, deletion, and optional macOS Keychain credentials.
- Shunt-style read gates, host-managed MCP tools plus `bulk-read`/`code-context` CLI commands, and guidance skills packaged for both hosts.
- Exact source passages and line provenance, BM25 retrieval, bounded Jev scoring, and a deterministic comparison backend.
- Component and complete-task evaluation runners, external correctness checks, and credential-free tests.
- Opt-in Jev-managed test generation through Codex/Luna, private staging, actual baseline/mutation checks and one bounded repair for a restricted pure-function profile; optional compact tickets apply exact accepted bytes through native CLI permissions.

The LLM still generates code and text and handles open-ended reasoning. Jev evaluates supplied options. Deterministic code controls policy and budgets; the host retains permissions and execution. Hooks do not expose hidden reasoning, and a delivered suggestion does not establish that a skill was used.

## Build and try locally

Use Node **24.21.0** (see `.nvmrc`) and npm **11.19.0**. The core targets macOS and Linux; host validation currently covers macOS only.

```sh
git clone git@github.com:dsandrade/jevra.git
cd jevra
npm ci
npm run check
npm run eval -- --backend deterministic
```

`npm run check` typechecks, builds the standalone CLI and both development plugins, and runs the tests. No API credential is needed. Built files are ignored by Git and must be rebuilt after a checkout or update.

Create a config that points to reviewed skills. This example uses only the synthetic fixture catalog:

```sh
node dist/jevra.mjs init --skills-root "$PWD/evals/fixtures/skills"
node dist/jevra.mjs doctor
```

`init` writes `$XDG_CONFIG_HOME/jevra/config.json` or `~/.config/jevra/config.json`, with mode `observe`, and refuses to overwrite an existing file. Replace `skillRoots` with your chosen absolute directories. Workspace config is never loaded automatically.

Provide `TYPESAFE_API_KEY` through your existing secure environment tooling, or initialize with an existing macOS Keychain service:

```sh
node dist/jevra.mjs init --skills-root "$PWD/evals/fixtures/skills" --keychain-service your-typesafe-key-service
```

These are alternative initialization commands. For an existing config, add `keychainService` manually. Only the service name is saved. The first Keychain access may require macOS authorization; an unattended read that exceeds its deadline falls back.

To evaluate a saved request, run `node dist/jevra.mjs evaluate --prompt-file /absolute/path/to/request.txt`. This command makes a live Jev call when eligible. Set `mode` to `advise` to prepare model-visible advice, or `disabled` to stop evaluation. Observe mode still makes API calls and adds hook latency.

For shunt-style reading, explicitly configure `bulkRead.roots` and the read hook; use [the example config](examples/shunt.config.json) and [shunt architecture](docs/shunt-parity.md). The helper sends shortlisted text from requested files to TypeSafe.

See [host setup and removal](docs/usage.md) before enabling a hook. Building or initializing Jevra does not activate it in an existing agent.

## Data sent and recorded

The skill router sends the current prompt and configured skill names, descriptions, and opaque IDs to TypeSafe. Skill bodies, source paths, transcripts, and other repository files are not sent by this module. Descriptions can still contain private information: choose the catalog deliberately.

The bulk reader and code-context helper send the focused question, opaque passage IDs, and shortlisted original source text from explicitly configured roots. In the default excerpt path, file-path metadata is kept local, but the source text itself can contain paths or private data. The opt-in focused reader additionally sends admitted corpus and relative metadata to Luna, then cited/counterevidence and claims to Jev; see its explicit privacy contract. The gate sends no source text and makes no API request. Explicit helper calls can consume TypeSafe usage even in observe mode.

The runtime reads skill bodies locally to validate bounded files and compute freshness hashes. Local JSONL traces contain hashed IDs, revisions, policy versions, reason codes, timing, and provider usage. They omit prompts, paths, skill text, and raw judgments. Default retention is seven days. Run `node dist/jevra.mjs clear-traces` to remove owned trace files.

## Evidence and limits

The [initial component report](evals/reports/2026-09-17-component-pilot.md) records 60/60 expected routing outcomes for Jev and 42/60 for a small deterministic baseline. These synthetic, author-labeled cases are a smoke dataset, not independent evidence of general accuracy. They do not measure coding-task quality or total host cost. The [full-task pilot report](evals/reports/2026-09-17-full-task-pilot.md) evaluates those separately with native, deterministic and Jev arms; estimates are not subscription bills.

The current reading pilot completed 12/12 tasks with 300/300 external checks. Claude’s Jev-arm estimate was about 6% lower, but its input tokens increased and it used the helper in only one of two tasks. Codex showed no consistent cost saving. These two synthetic tasks do not justify a default change or a subscription-savings claim.

The separate [test-artifact pilot](evals/reports/2026-09-17-artifact-comparison.md)
completed 12 cells with native, Luna-worker and Jev-managed arms. Jev did not show
consistent savings: aggregate input rose 28% on Codex and 135% on Claude, while
upper cost scenarios rose 1.4% and 26%. Parent-host overhead dominated. One native
file failed the restricted grammar, with functional correctness unknown; unequal
grammar guidance prevents a quality-superiority claim. [Compact artifact delivery](docs/artifact-materialization.md)
now removes required discovery and full-body copying from the opt-in native-ticket
path. Economic calibration, measurement parity and a new repeated comparison remain
next; the original pilot does not measure this delivery change. An optional
[economic routing gate](docs/economic-routing.md) now exists. Its initial question
diagnostic included an uncertain positive-benefit case; it is not enabled by
default. A scoped Claude routing-hook diagnostic observed compact artifact use,
with higher gross tokens on the tiny task and no savings claim.

The [16-case applicability diagnostic](evals/reports/2026-09-18-economic-applicability.md)
found a narrower Jev membership question more useful at the economic-only gate
(4/4 authored positives versus 0/4, no unsupported economic delegations in 12
blocking cases). A relevance-gate defect invalidated the evaluator's combined
route counters. Production routing is unchanged. The [corrected artifact protocol](evals/artifact-comparison-v2/protocol.md)
has offline fixtures, shared grammar, delivery/Jev/hook contrasts and accounting
utilities; it is a proposal, with no new complete host benchmark executed.

[Compatibility](docs/compatibility.md) distinguishes runtime tests, live host probes, and pending work. Caching, deduplication, durable session budgets, automatic installation/upgrades, skill-adherence measurement, and broader real-project comparisons remain in the backlog. No savings claim or default promotion to advise has been made.

## Documents and contributions

For continued development in Claude Code, read the [development handoff](docs/claude-code-handoff.md). It summarizes the latest managed-reader result and the next offline matched-comparison increment.

- [Product and technical specification](SPEC.md)
- [Implementation issues and acceptance criteria](ISSUES.md)
- [CLI-first worker v1 scope, readiness and implementation order](docs/v1-delivery-plan.md)
- [Worker architecture and fresh CLI execution contract](docs/worker-architecture.md)
- [Experimental Codex/Luna transport probe and measured overhead](evals/reports/2026-09-17-cli-worker-probe.md)
- [Managed worker contracts, limits and implementation boundary](docs/managed-worker.md)
- [First managed diagnostic: generation completed, continuation withheld](evals/reports/2026-09-17-managed-worker-probe.md)
- [Staged test artifacts, execution boundary and one-repair lifecycle](docs/test-artifacts.md)
- [Live artifact diagnostic: real checks and Jev acceptance](evals/reports/2026-09-17-test-artifact-probe.md)
- [Opt-in MCP configuration and native artifact review](docs/artifact-mcp.md)
- [Compact tickets and deterministic native artifact application](docs/artifact-materialization.md)
- [Compact delivery diagnostic: Codex adoption and Claude native completion](evals/reports/2026-09-18-materialization-host-probe.md)
- [Economic routing contract and measured-evidence requirements](docs/economic-routing.md)
- [Economic question failures and Claude routing-hook adoption diagnostic](evals/reports/2026-09-18-economic-routing.md)
- [Economic applicability comparison and evaluator audit](evals/reports/2026-09-18-economic-applicability.md)
- [Corrected whole-task comparison preparation](evals/artifact-comparison-v2/protocol.md)
- [Codex/Claude artifact wiring and observed adoption](evals/reports/2026-09-17-artifact-host-probe.md)
- [Complete-task artifact comparison, measured overhead and next changes](evals/reports/2026-09-17-artifact-comparison.md)
- [Shunt source audit: cost mechanisms, measurement limits and concrete changes](docs/shunt-cost-audit.md)
- [Current Shunt/Jevra architecture review and recommended smaller experiment](docs/shunt-architecture-review-2026-09-18.md)
- [Artifact comparison harness and frozen protocol](evals/artifact-comparison/README.md)
- [Development-brain architecture and first delivery slice](docs/development-brain.md)
- [Jev decision ownership, workflow concepts and stage map](docs/decision-architecture.md)
- [Architecture critique and recommended quality/cost delivery sequence](docs/architecture-critique.md)
- [Shunt comparison and token-efficiency experiment plan](docs/token-efficiency-plan.md)
- [Development and evaluation](docs/development.md)
- [Contributor and agent conventions](AGENTS.md)

Reference a stable planning ID from `ISSUES.md` in contributions. These IDs are not GitHub issue numbers. Write implementation and technical documentation in English.

See the [shunt parity map](docs/shunt-parity.md) for the shared control flow and explicit differences. By default, Jev selects evidence and generation stays in the main model. An explicitly configured experimental MCP profile can delegate pure-function test generation; no savings or default activation is implied. Spotify code is not a dependency, and its published context-reduction percentages are not Jevra results.

## License and service dependency

[MIT](LICENSE) covers this repository's original code and documentation. It does not license Jev model weights or grant TypeSafe API access. Users supply their own credentials.

This is an independent project, not an official OpenAI, Anthropic, Spotify, or TypeSafe product.
