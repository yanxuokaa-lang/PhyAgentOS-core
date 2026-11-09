![Agent Handoff Gate: a lead delegates a task, a worker produces a candidate, and an evidence gate returns a bounded continuation or a packet for lead review.](assets/handoff-overview.svg)

# Agent Handoff Gate

Agent Handoff Gate is an experimental protocol for delegated coding work. It checks the evidence behind a worker's `PASS` or `BLOCKED` report before the result reaches the lead agent, and describes how a controller can authorize one bounded continuation without replacing the lead's final review.

The project combines a readable specification, reusable task and evidence schemas, worked examples, a TypeSafe/Jev integration contract, and an evidence-evaluation benchmark. It grew out of practical attempts to reduce repeated reviews and administrative conversations between agents.

**Release status: experimental specification and offline evaluation kit, version 0.1.0.** This repository does not yet contain a production controller, a sandbox, or an installed adapter for any agent runtime. The included tools validate examples and reproduce selected historical metrics. They do not launch agents, contact an API, or grant permission to change a repository.

[Start with a worked example](docs/walkthrough.md) · [Read the protocol](docs/protocol.md) · [Inspect the results](evaluations/relayledger40/historical/REPORT.md) · [Understand the limits](docs/status.md) · [Local release checks](docs/release-checks.md)

## The problem at the handoff

A worker can report that every test passed while its tests never exercised the behavior requested by the lead. It can also stop with a useful diagnosis and a workable local fix because its ordinary repair budget is exhausted. In both cases, the lead receives work that might have been prepared more carefully before review.

The gate compares the task's requirements with the candidate and its evidence. Exact checks remain in code. A semantic evaluator such as Jev answers narrow questions about what the evidence actually supports. A separate policy determines whether to prepare a review packet, request an already authorized continuation, or return an unresolved issue to the lead.

A passing test, an evaluator's answer, an authorization to act, and the lead's acceptance remain separate records throughout the process.

## What happens to PASS and BLOCKED

| Worker report | Gate question | Permitted outcome |
| --- | --- | --- |
| `PASS` | Does the supplied evidence support each requirement at the agreed verification stage? | Send a review-ready packet, identify a local evidence gap, or request lead review. |
| `BLOCKED` | Is the proposed next step supported by the evidence and permitted by the existing contract? | Recommend a bounded continuation or send the specific decision to the lead. |
| Evaluator unavailable | Can the existing review process continue without the additional opinion? | Return to normal lead review, with the failed assessment recorded and no new grant. |
| Permission denial or hard stop | Is the proposed action prohibited or its authorization unresolved? | Stop that action and escalate without retrying it. |

A gate-approved packet is ready for review. It is never automatically accepted, merged, deployed, or authorized for production.

## Read or run the offline kit

Begin with the [walkthrough](docs/walkthrough.md), then inspect the [six small examples](examples/README.md). The examples contain synthetic material and explicitly labeled fixture assessments, not live Jev responses.

With Python 3.10 or newer, the following commands run without an API key or network access:

```sh
python -m unittest discover -s tests -v
python tools/replay_metrics.py
python tools/check_repository.py
```

JSON Schema validation is an additional, explicit development check:

```sh
python -m pip install -r requirements-dev.txt
python tools/check_schemas.py
```

Run installation only in a development environment you control. No command in the quickstart changes agent configuration, starts a worker, or calls TypeSafe. On systems where Python is named `python3`, use that command instead.

## What is in this repository

| Directory | Purpose |
| --- | --- |
| [`docs/`](docs/README.md) | Protocol, trust boundaries, design decisions, measurement, and adoption notes. |
| [`schemas/`](schemas/README.md) | JSON Schema contracts for tasks, evidence packets, assessments, and handoffs. |
| [`templates/`](templates/README.md) | Lead and worker instructions plus a conservative example policy. |
| [`examples/`](examples/README.md) | Complete, premature, blocked, prohibited, unavailable, and stale-result scenarios. |
| [`integrations/`](integrations/README.md) | TypeSafe request contract and the capabilities a future runtime adapter must provide. |
| [`evaluations/relayledger40/`](evaluations/relayledger40/README.md) | English benchmark edition and separately labeled historical results. |
| [`tools/`](tools/README.md) | Offline validation, prompt construction, and metric replay. |

## What the research currently supports

The historical RelayLedger-40 report records two Jev runs with 38/40 and 37/40 correct raw labels. At a preregistered `top_p` threshold of 0.80, each retained 22 decisive assessments, with no errors among those 22 on that packet. The same experiment also includes a native evaluator run with 40/40 raw accuracy.

These are small-sample observations, not production reliability or cost-saving claims. One baseline reported missing input sections, and both baseline semantic hashes were unresolved. The public result files are transcribed from the supplied report; the original full API responses are not included. Read the [historical report and corrections](evaluations/relayledger40/historical/REPORT.md) before comparing the runs.

The English benchmark is a translated edition with a new identity and new hashes. The historical measurements were not obtained on that translation.

## TypeSafe's role

The [TypeSafe API](https://docs.typesafe.ai/api) accepts a state and typed questions. Our reference design uses `Choice` to assess individual claims while preserving their probabilities. The controller remains responsible for scope, budgets, evidence integrity, authorization, and the final handoff.

The [integration contract](integrations/typesafe.md) distinguishes low model certainty, insufficient evidence, transport failure, and a prohibited action. The example threshold of 0.80 is experimental. It is not a universal safety threshold and is not TypeSafe's `confidence` field.

This is an independent project. It is not an official TypeSafe integration or a claim of endorsement. The official TypeSafe skill is not bundled or modified.

## Contributing

Contributions are most useful when they add a reproducible failure case, clarify a disputed claim, or demonstrate an actual before-return integration. Please describe what ran, what was mocked, and which claim the evidence supports. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

Original material is provided under the [MIT license](LICENSE). The project is maintained as an independent learning and research effort by Matt, with AI assistance in drafting, review, and tooling. External services retain their own terms and names.
