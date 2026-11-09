# Jev Cua Fastpath

`jev-cua` is a local Codex/Waku plugin for repetitive browser workflows whose controls, inputs, effects, and success evidence have been reviewed in advance. MCP is the connector; the workflow compiler, durable controller, Cua integration, and TypeSafe Jev policy live behind it.

```text
exact workflow -> local semantic snapshot -> closed candidates -> Jev veto/selection
               -> fresh snapshot -> one action -> exact postcondition -> repeat
```

This is not a general browser agent and it does not currently prove a “1000x” speedup. Jev receives a small closed decision problem, while deterministic code still owns authorization, dispatch, and verification. Benchmark Jev-on against a deterministic selector before claiming a latency or completion-rate gain.

## Current execution contract

- Live runs require one enabled manifest pinned by exact ID, version, and SHA-256 digest.
- The controller launches a fresh isolated Cua browser profile. Named/authenticated profiles are unsupported in v0.1.
- The bootstrap URL is HTTPS, credential-free, query-free, fragment-free, origin-allowlisted, and declared as a reviewed read-only landing navigation.
- Each step is `type`, `click`, or a bounded scroll to reveal an exact reviewed control.
- Jev chooses only among opaque IDs for locally compiled candidates plus `reobserve`, `abstain`, and `escalate`. It cannot invent URLs, selectors, values, coordinates, or Cua calls.
- The controller reobserves immediately before dispatch and rejects stale or ambiguous controls.
- A step advances only when its exact, page-bound `ensures` condition is true. A Cua success receipt, including `unverifiable`, never advances the workflow by itself.
- Exact terminal success present at startup returns without a Jev call or semantic action. Already-satisfied steps are reconciled without replay.
- Consequential and forbidden actions are not executed. Semantic risk patterns can raise—but never lower—the risk declared by a manifest.
- Once a mutation is attempted, every nonterminal exit requires reconciliation and never recommends fallback/replay.
- The requested browser delivery route is a least-authority boundary: DOM-only steps reject accessibility, global-input, or other silent fallback receipts. Session cleanup is explicit in every completed result; an unconfirmed cleanup fails closed as `unknown` with reconciliation required.
- A durable global execution barrier is written before browser setup. Production clears it only after positive session cleanup and either no attempted mutation or a verified terminal result. Unconfirmed cleanup, process death, and nonterminal post-mutation outcomes quarantine all later live runs across restarts.
- The global desktop lease, execution barrier, and at-most-once ledger use a fixed per-user directory, independent of caller-configurable trace storage. The guarantee is per caller-supplied run key; a different key, deleted state, or an out-of-band action is outside it.

The live runtime accepts exactly Cua Driver `0.28.2`, checks its advertised action-receipt schemas, and on macOS verifies the installed `/Applications/CuaDriver.app` signature against identifier `com.trycua.driver` and team `YCK386LBJ7`. A caller-supplied driver binary is not accepted for live macOS use.

## Data boundary

TypeSafe receives only:

- the fixed reviewed goal;
- redacted fixed candidate descriptions;
- candidate risk labels and opaque candidate IDs; and
- minimal prior-action metadata.

It does not receive the page URL/origin, title, outline, raw page content, semantic refs, action arguments, coordinates, or workflow input values. Cua and the target page still process locally dispatched values. `allowed_disclosure_origins` records the human-reviewed recipient page; it is not a network/DLP firewall, because scripts on that page may transmit data elsewhere.

Review TypeSafe’s [privacy policy](https://typesafe.ai/legal/privacy-policy) and [data-processing terms](https://typesafe.ai/legal/data-processing) before real data is used.

## Threat-model limits

The plugin is a reliability and least-authority layer inside Codex/Waku, not a hard sandbox against an agent with unrestricted same-user shell or computer access. Such an agent can edit local manifests, write login-Keychain items, bypass this MCP and invoke Cua directly, or deliberately race a verified executable path between signature checking and process launch.

The Keychain workflow digest is therefore a tamper-evident local trust pin, not proof of fresh human presence. A hard security boundary requires a separately trusted service/OS identity that owns the Cua and TypeSafe credentials, exposes only this narrow protocol, uses a bounded Cua capability manifest, and obtains user-presence-bound approvals. v0.1 also does not auto-execute external submissions, sends, purchases, permissions, uploads, deletion, credential entry, or other consequential work.

An exact origin, path, label, and local manifest do not attest the behavior of the remote site. A compromised site can preserve reviewed labels while changing what a nominally reversible control does, and postcondition checks necessarily occur after dispatch. Re-review and version-bump a workflow whenever the site changes; do not treat this plugin as protection from a malicious origin.

## Setup

Requirements:

- macOS and Node.js 24.21+
- the signed Cua Driver `0.28.2` application in `/Applications`
- a Cua-compatible Chromium browser; the validated local benchmark setup uses a dedicated Microsoft Edge installation
- Cua Accessibility and Screen Recording permissions for live use
- a TypeSafe API key for Jev-backed runs (the deterministic benchmark arm does not need one)

The MCP launcher deliberately uses Homebrew's isolated Node 24 runtime when it
is present. TypeSafe SDK 0.6.0 has a confirmed cancellation crash on supported
Node 20/22 releases; Node 24.21 is the verified workaround. Install it without
changing your default Node version:

```bash
brew install node@24
brew install --cask microsoft-edge
```

```bash
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
npm install
npm run check
cua-driver telemetry disable
cua-driver permissions grant
/usr/bin/security add-generic-password -U \
  -s ai.typesafe.jev-cua \
  -a typesafe-api-key \
  -w
```

Enter the TypeSafe API key only at the resulting Keychain prompt. Keeping bare
`-w` as the final argument prevents the secret from appearing in shell history
or process arguments.

List the workflow to obtain its exact digest, review the manifest, then pin that digest:

```bash
/usr/bin/security add-generic-password -U \
  -s ai.typesafe.jev-cua.workflow \
  -a '<workflow-id>@<version>' \
  -w '<64-character-workflow-digest>'
```

Run `jev_cua_doctor`, then `jev_cua_list_workflows`. Use a new shadow-only run key to inspect the static `shadow_plan`; shadow launches no browser and calls no TypeSafe service. If the plan is correct, use a distinct new key for the live attempt. Never mint another live key to replay an uncertain action.

### Recovering a quarantined live run

There is intentionally no MCP tool that clears the execution barrier. If `jev_cua_doctor` reports `live_execution_safety` as blocked, use this trusted-operator procedure from a trusted terminal:

1. Record the exact `runId`, `session`, and barrier state shown by the doctor, and inspect the run with the original run key using `jev_cua_get_run`. A crash after the barrier was cleared but before ledger completion can leave a ledger-only blocker; in that case derive the current session as `jev-cua-` plus the first 12 hexadecimal characters of the run ID with hyphens removed. The recovery CLI also accepts the earlier `8hex-3hex` session form.
2. Run `cua-driver sessions --json`. If that exact session is still present, run `cua-driver revoke --session '<session>'`, then confirm it is absent with another `sessions --json` call.
3. Reconcile the target site's real state. Browser cleanup does not prove that a server-side effect did or did not happen.
4. From an interactive trusted terminal, run the local recovery command with those exact identifiers:

   ```bash
   npm run reconcile-live -- \
     --run-id '<run-id>' \
     --session '<session>'
   ```

5. Review the displayed identity and type the exact requested `RECONCILED <run-id>` phrase. This interactive phrase provides deliberate audit friction; it is not OS-backed proof of human presence, and malware running as the same user can automate it. The command refuses noninteractive input, any live Cua session, an untrusted Cua installation, and mismatched identities. It writes a private acknowledgement bound to the SHA-256 of that exact run record, then archives the owner-matched barrier when one remains. It deliberately leaves the original HMAC-keyed run ledger in place, so a completed old key returns its prior result and an interrupted old key remains permanently reserved; neither can execute again.

6. Run `jev_cua_doctor` again. Resume live work only when both the barrier and durable-run scan report unblocked. The archived barrier, acknowledgement, and original ledger form the retained audit trail.

The checked-in reference workflow is intentionally disabled. The bundled entrypoint is `mcp/server.cjs`.

Do not recursively strip signing metadata from a personal browser to make it pass Cua's strict executable check. Use a clean, dedicated browser installation and verify its signature instead.

## Contract-reproducible benchmark

The owned fixture is deployed at `https://jev-cua-benchmark-fixture.erons.workers.dev/v6/catalog-search`. The runner pins its exact version, response SHA-256, complete security-header set, workflow digest, fixed public inputs, controller settings, model identities, and seeded order. It records the installed Cua and browser executable SHA-256 digests, the actual TypeSafe SDK version, and the package-lock digest. It fetch-verifies the HTTP contract immediately before every trial and after the batch. The page visibly states the exact fixture contract, and every executable field/control has that V6 contract marker in its exact accessible name; a candidate cannot exist against an unversioned lookalike. Each trial opens a fresh isolated browser profile and performs the same three-step catalog QA task: type `chicken`, sort price low-to-high, and enable the sale filter.

That two-sided check is strong drift detection, not a cryptographic binding between the separately fetched bytes and the page Cua observes. A malicious or split-serving origin could theoretically return the pinned body to the verifier and a different page carrying the same marker to the browser. Keep the fixture on an isolated owned origin; do not generalize this benchmark trust model to an untrusted site.

“Contract-reproducible” does not mean model-weight reproducible. `jev-1.13.0` is a remote service identity, and TypeSafe can change infrastructure or behavior behind that name without supplying a weight or service-revision attestation. Reports are evidence for the observed dates and recorded contract, not a promise that later provider behavior will match.

Run the credential-free deterministic baseline:

```bash
npm run benchmark -- \
  --arm deterministic \
  --pairs 30 \
  --warmup-pairs 3 \
  --seed catalog-search-v1
```

After the TypeSafe key is in Keychain, run the balanced paired comparison:

```bash
npm run benchmark -- \
  --arm both \
  --pairs 30 \
  --warmup-pairs 3 \
  --seed catalog-search-v1
```

The primary latency is monotonic elapsed time around `controller.run()`. Keychain lookup, fixture verification, and Cua readiness preflight are deliberately outside that timed interval. Durable JSONL trace writes, fsyncs, and positively confirmed session cleanup remain inside it, matching production controller behavior. Ambient controller-tuning environment variables are ignored. The runner:

- rechecks the signed Cua runtime, tool contract, health, permissions, and disabled telemetry before every trial;
- balances adjacent Jev-first and deterministic-first pairs;
- records verified completion with Wilson intervals, paired completion outcomes with exact McNemar analysis, all-outcome latency, both-verified paired latency, action timing, actual Cua delivery routes/effects, and known returned token usage;
- marks provider-failure token usage unknown because a timed-out request may still have consumed billable tokens;
- rejects a verified result unless it contains exactly three ordered execute decisions, actions, receipts, and postconditions; bounded read-only `reobserve` decisions are counted separately; and
- never retries the same run. The disposable fixture may continue with the next statistically independent trial only after positive isolated-session cleanup; unproven cleanup, runtime drift, fixture drift, cancellation, or contamination stops the batch.

Reports and content-free traces are written under ignored `benchmark-results/` directories with modes `0700` and `0600`. One exclusive batch lease prevents two schedules from interleaving. A dirty/unavailable source tree or mismatched installed TypeSafe SDK stops before a browser trial; the source commit and worktree are checked again after the batch. Every terminal stop marks measurements invalid and publishes no statistical summary. An interrupted batch remains marked `running`; the runner refuses to start another batch until its durable ledger is inspected. Do not use the keyboard or browser during a batch: the desktop lease excludes other compliant controllers, not a human or a process that invokes Cua directly.

The report records the installed Microsoft Edge version, but Cua 0.28.2 does not identify the launched browser executable in its `browser_prepare` receipt. Treat that field as environment inventory, not proof that a particular trial used Edge.

At each decision, the compiled controller exposes only the next executable reviewed step plus three stop routes. The benchmark measures Jev's marginal latency, token cost, and veto/reobserve behavior inside that controller; it cannot demonstrate better planning, general computer-use reasoning, or a “1000x” improvement. Thirty measured trials per arm are exploratory: even 30/30 verified gives only about an 88.6% Wilson lower bound, and its p95 estimate is unstable.

## Why Cua + Jev

Cua’s semantic snapshots and exact refs address UI grounding; they do not supply workflow authorization, durable idempotency, or postcondition semantics. The v0.1 compiler exposes only the exact next executable workflow step plus the three stop/reobserve routes, so Jev currently acts as a probabilistic veto—not as a general planner. That extra call may reduce rather than improve speed; benchmark it against a deterministic bypass. The controller supplies the state machine and fails closed when the page, receipt schema, decision, or evidence falls outside its contract.

Relevant upstream material: [Cua Driver installation](https://cua.ai/docs/how-to-guides/driver/install), [agent connection](https://cua.ai/docs/how-to-guides/driver/connect-your-agent), and [semantic snapshots](https://cua.ai/docs/reference/cua-driver/browser-semantic-snapshots).
