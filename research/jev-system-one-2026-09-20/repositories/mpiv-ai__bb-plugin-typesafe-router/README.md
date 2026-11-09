# TypeSafe Router

A BB plugin that picks the harness, model, and reasoning effort for a thread's
**first message**, using TypeSafe (Jev), and asks you to confirm before it locks
them in.

Routing is opt-in, per thread: it happens only when you pick **TypeSafe Router**
as the provider on the New Thread page. A thread you start directly on Codex,
Claude, or any other harness is never touched.

BB fixes a thread's harness once the thread runs. The first message is the only
moment that choice is still open, so that is the only moment this plugin acts.
Follow-ups, steers, retries, and background threads dispatch untouched.

## Requirements

- **BB** `>= 0.43` with Plugin SDK `>= 0.4.87`. These are the `engines` in
  [`package.json`](package.json); BB refuses to install the plugin on an older
  runtime.
- **A TypeSafe account and API key** from <https://console.typesafe.ai>. This
  plugin does not ship a key and cannot route without one.
- **At least one real agent harness already working on that machine** — Codex,
  Claude Code, or another BB provider you have already used successfully. The
  TypeSafe Router picker row is not a harness and cannot run a turn; it exists
  only so BB will enable **Send** before a harness has been chosen.

Catalogs are **per machine**. TypeSafe only chooses among the harnesses and
models that the thread's machine actually has, so a machine with one harness
installed will keep being routed to that harness.

## Install

```
bb plugin install git:https://github.com/mpiv-ai/bb-plugin-typesafe-router@v0.1.0 --yes
bb plugin config typesafe-router set typesafeApiKey 'YOUR_KEY'
bb plugin reload typesafe-router
```

Quote the key — API keys can contain characters your shell would otherwise
interpret.

Without a key the plugin reports `needs-configuration` and blocks nothing on a
thread that already has a real harness.

## First use

1. **New Thread** → pick **TypeSafe Router** as the provider.
2. Pick its one model, **Choose harness and model**.
3. Type your message and press **Send** *once*.
4. The composer is replaced by a wait card reading "TypeSafe is selecting the
   right harness and model." Nothing is written to the timeline yet.
5. A confirmation card appears with the harness, model, and effort TypeSafe
   chose; the effort is editable there. Press **Yep** and the thread continues
   there. **Cancel** declines, and nothing runs.

Because BB cannot swap a running thread's harness, confirming moves your
message to a new thread on the chosen harness. A thread started on the picker
row always takes that path, since the picker row is never a candidate. Once the
thread starts, the harness is locked; the model can still be changed normally.

## Configuration

Open **Settings → Tools → TypeSafe Router**. The automatic form contains only
`typesafeApiKey` (secret). The custom section contains one Route first messages
switch and the live harness switches. Routing is enabled by default. A **How
routing works** section under the switches is the short user guide.

Preferences are stored in `bb.storage.kv` and apply on the next first message.
The former `enabled`, `includeHarnesses`, `excludeHarnesses`,
`maxModelsPerHarness`, and `curationMode` settings are migrated once. Include
and exclude restrictions are preserved; the old cap and mode are archived but
ignored. Exclude wins over include. An empty result never calls TypeSafe and
rejects the held first message. The router stub is never a candidate.

BB SDK 0.4.87 cannot read undeclared settings. The migration uses
`bb.server.experimental_dataDir` to open `bb.db` read-only and selects only
this plugin's five non-secret preference keys from `plugin_settings`. It never
reads key material or writes core tables. If migration fails, loading fails
without recording completion, so an upgrade cannot silently widen exclusions.
Subsequent reads and writes use plugin storage only. This migration depends on
the BB table schema and is covered with a temporary SQLite fixture.

### Capability knowledge and model shortlist

The router classifies the truncated first message locally as coding, agents,
general, scientific, writing, or mixed. Unknown or tied signals use mixed.
It collapses family aliases, ranks by that axis, then offers at most eight
models per harness. Unmeasured models retain catalog order after scored models;
the default wins only when choosing among aliases of the same family.

`datasets/axis-scores.json` vendors public benchmark results with sources and
a capture date. Scores are percentiles within each benchmark cohort, averaged
per axis. Mixed averages the available axes. GDPval-AA knowledge work is the
writing/office-work proxy; AutomationBench supplies the agents/ops axis.
These small, heterogeneous cohorts are routing evidence, not a universal model
leaderboard. Missing results are null and newer families do not inherit an
older version's numbers. No benchmark is fetched during routing.

Both Choice calls receive authored `what`, `not_for`, `tools`, and `examples`
from `datasets/capability-cards.json`. Unknown cards say capabilities are
unverified. Tools depend on the installed harness configuration. There are
still exactly two serial Choice calls, followed by **Yep**.

## Privacy

Only the first message's text is sent to TypeSafe, truncated to 4000
characters, along with the project name and the live names/descriptions, authored capability cards, and snapshot ranks
of the candidate harnesses and models. When an effort call is made, the chosen
model's own effort ladder — level names, position, and relative cost, not
usage or billing data — goes too. The repository, the timeline, and later
messages are not sent.

## Troubleshooting

**"TypeSafe Router chooses a harness; it cannot run a turn itself."** The thread
is sitting on the TypeSafe Router picker row and routing did not produce a
runnable harness — the message says why in parentheses: usually no API key,
routing disabled, or you declined the proposal. It also happens if you hit
**Send now** on the queued row; Send now is a core bypass that skips the hook by
design, and on a picker-row thread there is no harness to fall back to, so the
message is rejected instead of started. Set the key and reload, or pick Codex
or Claude in the composer and send again.

**The plugin reports `needs-configuration`.** No API key is set. Run the
`bb plugin config ... set typesafeApiKey` command above, then
`bb plugin reload typesafe-router`.

**TypeSafe keeps choosing the same harness.** Catalogs are per machine, and the
picker row is excluded from them. If that machine only has one real harness
installed, that is the only candidate. Check the **Routing preferences** section
on the plugin's settings page too — a harness switched off there is not offered.

**"every available harness is switched off in this plugin's settings."** Your
`includeHarnesses` / `excludeHarnesses` combination leaves nothing to route to,
so the plugin refused rather than calling TypeSafe or starting a turn on the
picker row. Switch a harness back on in **Routing preferences**; the settings
page shows the same warning as soon as the count reaches zero.

**Send is disabled on the New Thread page.** BB needs both a provider and a
model. Pick **TypeSafe Router** *and* its **Choose harness and model** row.

**Nothing is held at all.** Only a first message sent on the **TypeSafe Router**
row is routed. A thread started directly on Codex, Claude, or any other harness
is never held, and neither are follow-ups, steers, retries, joined turns, hidden
worker threads, threads started by an agent or the system, or threads another
plugin spawned.

## How it works

`message.dispatch` is a checkpoint with a 10-second fail-closed budget, so the
hook itself only reads cheap state and answers. It holds the first message with
`{ action: "wait" }` and runs the expensive part off the hook:

1. Read this machine's live catalogs (`bb.sdk.providers.list` / `.models` for
   the thread's host — catalogs differ per machine, and one harness can offer
   800+ models). Drop the harnesses your settings exclude, then curate each
   survivor to at most eight models for the locally classified task axis. The catalogs themselves are
   always fetched live; the settings only trim what Jev is shown.
2. Two or three sequential TypeSafe Choice calls: **which harness**, then
   **which model inside that harness**, then — when that model offers more
   than one reasoning effort — **how much effort**. Hierarchical, because these
   are separate judgements and a flat 40-label question is none of them. The
   effort shown on the New Thread page is not consulted: BB reports it as a
   choice whether you touched it or not, so the confirmation card is where you
   override the proposal.
3. Replace the composer with a confirmation card showing the proposed harness,
   model, and effort. Effort is editable right there when the model offers a
   choice. **Yep** applies it.
4. Same harness → set the model on this thread and release the held message.
   Different harness → spawn a new thread on it carrying the same input, then
   reject and archive this one.

Then `experimental_hooks.recheck("message.dispatch")` asks core to re-decide the
held row.

The picker row never runs a turn: its bridge refuses `turn/start`, it is
excluded from the catalog TypeSafe chooses from, and any dispatch that would
start a turn on it is rejected with a message telling you to pick a real
harness instead.

## Layout

- `lib/provider.ts` — the picker row's id, model, and the one predicate that
  keeps it out of everything else. Pure.
- `lib/provider-bridge.ts` — the minimum bridge: handshake, one model, and a
  refusal for `turn/start`.
- `host.ts` — the `bb.host` artifact, which exists only to carry that bridge.
- `lib/catalog.ts` — curation and the harness filter. Pure; no network.
- `lib/preferences.ts` — stored harness lists
  parsed into the decisions routing makes. Pure.
- `lib/policy.ts` — what to intercept and what to answer on a re-attempt. Pure.
- `lib/router.ts` — the harness, model, and effort Choice calls, against an
  injectable client.
- `server.ts` — wiring: settings, the hook, the routing pass, RPC.
- `app.tsx` — the composer banner, the confirmation card, and the settings
  section on the plugin's page.
- `skills/typesafe-router/SKILL.md` — what agents are told about routing.

## Docs

[docs/](docs/README.md) explains the plugin from the inside: the architecture,
the dispatch hook and routing state machine, the three TypeSafe calls, how
execution settings are carried, configuration and UI, and development.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the local development loop, and
[CONTRIBUTORS.md](CONTRIBUTORS.md) for authorship.

## License

MIT — see [LICENSE](LICENSE).
