# Gavel

**Stop burning LLM calls on classification. Route bugs, triage failures, and gate PRs in 200ms for $0.00002.**

Gavel is an OpenClaw plugin that gives AI agents a fast, cheap, structured decision tool for development workflows. It wraps TypeSafe's Jev model (`typesafe/jev-1.13`) through the OpenRouter decisions API and teaches agents exactly when to use it — and when not to.

## What it does

Every time your agent classifies an incoming bug, routes a PR, gauges severity, or decides whether a change needs TDD — that's a classification problem, not a reasoning problem. Gavel makes that decision in 200ms for $0.00002 instead of burning a 2-second, $0.01-0.05 LLM call.

It can't hallucinate an answer outside your defined options. It returns calibrated confidence you can gate actions on. And it never generates prose when all you needed was a label.

## Development use cases

| Use case | What Gavel decides | Primitives |
|----------|-------------------|------------|
| **Incoming task routing** | Bug or feature? How complex? Urgent? Blocker? | choice + score + noul |
| **Bug triage** | Severity? Category? Needs TDD? Assign to whom? | score + choice + noul |
| **PR review gate** | Review depth? Risky? Needs tests? | choice + noul |
| **Test prioritization** | Failure type? Flaky? Needs investigation? | choice + noul (batch 50 in 2s) |
| **Scope gate** | Single file or architectural? Needs decomposition? Irreversible? | choice + noul |
| **Incident routing** | Severity? Action level? Customer-facing? Data risk? | score + choice + noul |

See the [white paper](docs/GAVEL-WHITE-PAPER.md) §8 for full JSON payloads and response examples for each use case.

## What it doesn't do

Write code. Fix bugs. Review diffs. Debug root causes. Design architecture. Generate prose of any kind.

**That's the point.** Gavel handles the routing decision so your LLM can focus on the actual work.

## Three primitives

| Primitive | Question | Output |
|-----------|----------|--------|
| **Noul** | Is this true? | Probability 0–1 |
| **Choice** | Which option? | Selected option + distribution + confidence |
| **Score** | What level? | Rubric level + distribution + confidence |

## Architecture

```
Developer says "fix the payment webhook 500s"
         │
         ▼
   GAVEL classifies (200ms, $0.00002)
   intent=bug  complexity=moderate  urgent=yes  blocker=yes
         │
         ▼
   Agent routes: immediate priority, spawn worker with TDD contract
         │
         ▼
   LLM investigates and writes the fix (reasoning + code)
         │
         ▼
   LLM reviews the diff (reasoning + quality gate)
         │
         ▼
   Done
```

## Requirements

- OpenClaw gateway >= `2026.9.4` (plugin SDK + tool registry compatibility)
- An [OpenRouter](https://openrouter.ai) API key with access to `typesafe/jev-1.13`

### Compatibility

| OpenClaw version | Status |
|-----------------|--------|
| `< 2026.9.4` | Not compatible — plugin SDK API changed |
| `>= 2026.9.4` | Fully tested and supported |
| Future versions | Should work; re-run test suite to verify |

The plugin uses `definePluginEntry` and `defineToolPlugin` from the OpenClaw plugin SDK, plus TypeBox for schema validation. These APIs were stabilized in `2026.9.4`. Earlier versions may not register the tool correctly.

## Installation

1. Copy this directory into your OpenClaw extensions directory:

   ```bash
   cp -r gavel ~/.openclaw/extensions/gavel
   ```

2. Install dependencies and build:

   ```bash
   cd ~/.openclaw/extensions/gavel
   npm install
   npm run build
   ```

3. Set the environment variable in the gateway environment:

   ```bash
   export OPENROUTER_API_KEY=sk-or-...
   ```

4. Enable the plugin and grant the tool. Plugin id is `jev` (even if the directory is named `gavel`). `tools.profile: "coding"` does **not** include `group:plugins`, so a loaded plugin still will not appear until you allow `jev_decide`.

   Global (enough if no agent overrides `tools.alsoAllow`):

   ```json5
   {
     plugins: { entries: { jev: { enabled: true } } },
     tools: {
       profile: "coding",
       alsoAllow: ["jev_decide"],
     },
   }
   ```

   If an agent already has its own `agents.entries.<id>.tools.alsoAllow` (for example `message` only), **add `jev_decide` there too**. A per-agent `alsoAllow` list does not pick up the global extra by itself.

   ```json5
   {
     agents: {
       entries: {
         example_agent: {
           tools: { alsoAllow: ["message", "jev_decide"] },
         },
       },
     },
   }
   ```

5. Restart the gateway with the native command (not a guessed systemd unit name):

   ```bash
   openclaw gateway restart
   ```

6. Verify:

   ```bash
   openclaw plugins inspect jev   # Status: enabled
   ```

   Then confirm `jev_decide` is in the agent tool list and call it once. Plugin loaded + restart is not enough if the tool is still policy-filtered.

## Usage

Agents call `jev_decide` with a state string and typed questions:

```json
{
  "state": "the payment webhook is returning 500s",
  "questions": {
    "intent": {
      "type": "choice",
      "instructions": "What kind of work is this?",
      "criteria": {
        "bug": "Something is broken and needs fixing",
        "feature": "New functionality or enhancement",
        "research": "Investigation or exploration",
        "ops": "Infrastructure, config, deployment",
        "status": "Status check or quick question",
        "chat": "Conversation or discussion"
      }
    },
    "complexity": {
      "type": "score",
      "instructions": "How complex is this?",
      "criteria": ["Trivial", "Simple", "Moderate", "Complex"]
    },
    "is_urgent": {
      "type": "noul",
      "instructions": "Does this require immediate action?",
      "criteria": {
        "true": "Production is down, data loss, security issue",
        "false": "Can be queued normally"
      }
    }
  }
}
```

Returns in ~200ms:

```
intent:      bug         (confidence=0.94)
complexity:  2 (Moderate) (confidence=0.81)
is_urgent:   0.87
```

See [SKILL.md](./SKILL.md) for complete guidance: when to use Gavel, fallback strategy, system discovery questions, and example routing patterns.

## Performance

- **Single call:** ~200ms, ~$0.00002
- **Five questions in one call:** ~600ms (parallel evaluation)
- **50 test failures triaged:** ~2 seconds, ~$0.0002
- **Context savings:** 40% reduction vs LLM-only classification (see [case study](docs/CASE-STUDY-CONTEXT-SAVINGS.md))

## Testing

Tests hit the live OpenRouter decisions API and require `OPENROUTER_API_KEY`:

```bash
cd tests
python3 -m pytest -v
```

32 tests, all passing. No mocks — every test calls the real API.

## Documentation

- [SKILL.md](./SKILL.md) — agent skill: when to use Gavel, fallback strategy, system discovery
- [docs/GAVEL-WHITE-PAPER.md](./docs/GAVEL-WHITE-PAPER.md) — architecture, testing, risks, escapements, 6 development use cases
- [docs/CASE-STUDY-CONTEXT-SAVINGS.md](./docs/CASE-STUDY-CONTEXT-SAVINGS.md) — 40% context savings on real classification work
- [tests/RESULTS.md](./tests/RESULTS.md) — latest test run findings

## License

MIT
