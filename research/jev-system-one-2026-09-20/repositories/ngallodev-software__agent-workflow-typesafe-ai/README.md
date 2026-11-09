# Agent-Workflow TypeSafe AI

`agent-workflow-typesafe` is an external Agent-Workflow plugin that makes
optional [TypeSafe AI](https://typesafe.ai/) API calls through its Jev/System
One typed-decision API. It augments bounded decisions with Choice, Noul, and
Score evidence while Agent-Workflow retains deterministic authority.

## What it does

- Projects bounded, redacted task or skill evidence into TypeSafe AI questions.
- Calls the optional TypeSafe AI/Jev API and normalizes typed answers into
  versioned, secret-free semantic receipts.
- Provides advisory routing metadata: task class, interaction need, and
  semantic consequence/risk.
- Evaluates whether a skill directs a required behavior, plus independent
  completeness and actionability evidence.
- Reports compatibility and credential-free diagnostics through
  `agent-workflow typesafe compatibility` and `doctor`.

All outputs are advisory `no_action` evidence. The plugin never changes
Agent-Workflow routing, executor or model policy, lifecycle, evaluation,
review, or acceptance. Missing credentials, an unavailable SDK, uncertain
answers, and service failures return distinct no-action outcomes.

Install the base package for discovery, compatibility checks, and semantic
receipts. Install `agent-workflow-typesafe[typesafe]` only to make live TypeSafe
calls. Install `agent-workflow-typesafe[eval]` for the shared comparative-evaluation
library, or `agent-workflow-typesafe[typesafe-eval]` for both optional capabilities. `TYPESAFE_API_KEY` is read only by the optional live adapter;
it is never written to configuration, receipts, or logs.

Enable it in Agent-Workflow configuration:

```toml
[plugins]
enabled = ["agent-workflow-typesafe"]
```

Then use `agent-workflow typesafe compatibility`, `doctor`, `advise-routing`,
or `evaluate-skill`. Live calls require both the optional extra and the normal
runtime environment key. The distribution and entry-point names remain stable
for host compatibility even though the public repository is named
`agent-workflow-typesafe-ai`.

## Comparative evaluation

Comparative evaluation is now split across a dependency-neutral shared library and
this provider-specific plugin. `agent-workflow-comparative-eval` owns canonical
comparison contracts, datasets, pairing/metrics/statistics, and neutral evidence.
This plugin retains TypeSafe/Jev execution and candidate telemetry only.

For the 0.1.x migration window, `agent_workflow_typesafe.evaluation` remains as a
compatibility facade. With the `[eval]` extra installed it delegates generic work to
the shared library; without that extra it uses the frozen 0.1.0 implementation so
base plugin installs do not acquire a new required dependency. Existing
`agent-workflow-typesafe/.../v1` observation artifacts remain readable; new
integrations should use the neutral shared-library schema namespace.

See [docs/comparative-evaluation/README.md](docs/comparative-evaluation/README.md).
