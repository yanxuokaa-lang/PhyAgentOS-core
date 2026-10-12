# Scene Understanding Provider Failure Diagnosis (2026-10-12)

## Scope

This diagnosis covers the generic semantic-provider chain used by the persistent
RoboTwin adapter. It does not add or depend on RGB, color, object, benchmark, or
destination-specific behavior.

## Authoritative evidence

Task `task_76d05c0a4ef84ebb` reached a post-unknown-Action refresh revision and
successfully completed the fresh synchronized observation and capability query:

- scene revision: `8c6577a96f864fc9987665f87003ad4c-2`
- observation: `observation://8c6577a96f864fc9987665f87003ad4c-2/head_camera`
- capture skew: `0 ms`
- freshness at understanding selection: `107 ms`
- `manipulation.capabilities`: successful
- `scene.understand`: unavailable, `understanding_provider_error`,
  `failure_stage=provider`, `retryable=false`, `provider_route=none`

The bounded diagnostic JSONL contains three repeated provider-chain failures for
the same scene revision:

| UTC time | route | elapsed | result |
| --- | --- | ---: | --- |
| 01:40:32 | primary | 8.451 s | error |
| 01:40:55 | none | 32.598 s | `contract+provider_failure` |
| 02:27:11 | primary | 8.249 s | error |
| 02:27:44 | none | 41.618 s | `contract+provider_failure` |
| 03:54:32 | primary | 8.357 s | error |
| 03:55:05 | none | 41.287 s | `contract+provider_failure` |

The task entered bounded `awaiting_replan` with a deadline and later became
`failed` after no valid semantic evidence arrived. This is not a motion,
binding, target, or `motion_authorized=false` failure.

## Root cause

The primary Qwen provider and configured fallback both failed before producing a
semantic scene result. The old fallback seam projected only the concatenated
class (`contract+provider_failure`) and `route=none`. That was insufficient to
answer which provider failed with which class or whether a bounded HTTP status
indicated a contract mismatch, service error, authentication failure, or
transport failure.

The adapter intentionally did not persist exception text, provider payloads,
credentials, or filesystem paths. That safety boundary was correct, but the
diagnostic schema was too small. A version number, record primary key, or task
settlement cannot reconstruct facts discarded at the provider boundary.

An independent read-only replay of the same local Qwen request reproduced an
`InternalServerError`; the endpoint was subsequently connection-refused and its
vLLM process was absent. This corroborates local provider instability under the
multimodal structured-output request, but does not by itself prove that every
historical failure had the same underlying server exception. The new per-route
code is required to distinguish those cases on the next occurrence.

## General fix

The existing provider-neutral boundaries now preserve bounded diagnostics:

- primary and fallback route names;
- independent `provider_error_class` values;
- independent bounded `provider_error_code` values such as `http_500`,
  `contract_output`, `timeout`, or `missing_api_key`;
- the existing combined `provider_error_class` for compatibility.

The values are projected through the adapter, lifecycle wrapper, Core Query
result, and persistent JSONL sink using the existing token validation. Raw
exception messages, response bodies, credentials, model output, and paths never
cross the boundary.

This change does not automatically retry a failed Query, refresh an unchanged
scene, replay an Action, weaken a readiness gate, or authorize motion. A true
provider outage remains fail-closed and is released only through the existing
Runtime/provider readiness lifecycle. Once the provider is healthy, the normal
AgentLoop may resume the same task and obtain new semantic evidence.

## Related historical incident and ownership boundary

The earlier `task_e37a4626b085484f` incident was different: Qwen failed, GPT
fallback produced semantic output, and a later LocateAnything proposal worker
failed. That was an enrichment failure, not a dual semantic-provider failure.
The generic `failure_stage` projection now keeps those cases separate so Core
does not send a worker failure through the semantic-provider readiness path.

Ownership remains split as follows:

- Runtime/worker owns process lifecycle, exit state, and bounded worker facts.
- The Adapter maps provider and enrichment failures to neutral stage/class/code
  fields and never authorizes motion.
- Core owns Query validation, persisted settlement, and provider-block
  classification.
- AgentLoop/Coordinator owns bounded recovery and readiness handoff; it never
  replays an Action or creates a replacement task for a provider failure.

Missing semantic evidence continues to block binding and every downstream
motion node. Calibration, workspace, collision, IK, admission, possession, and
`motion_authorized` semantics are unchanged.

## Validation

- RobotWin provider, Core projection, persistent-host, OpenAI/Qwen and
  single-view tests: `94 passed`.
- Core AgentLoop/planning/recovery suites: `263 passed`.
- Ruff, compileall, and `git diff --check` all passed.
- Validation is no-motion: no AgentTask, Gateway Query/Action, camera read,
  simulator step, or physical execution is part of this change.

## Implementation review

The seven-dimension review found and fixed one generic edge case: an empty
primary result entered fallback without being retained in the in-memory route
diagnostics. The fallback now records `provider_failure/empty_result`, clears a
stale route at the start of each invocation, and keeps the existing fallback
and readiness behavior. The review found no architecture, correctness,
recovery/idempotency, robotics-safety, extension-compatibility, observability,
or AgentLoop-convergence issue remaining.

The changed boundaries are:

- `scene_understanding_fallback.py:L9-L125,L204-L291` and
  `test_scene_understanding_fallback.py:L65-L81,L84-L234`: independent route
  facts, bounded codes, and empty-primary regression.
- `qwen3_vl_vllm_scene_understanding.py:L75-L177,L200-L331`,
  `qwen3_vl_vllm_lifecycle.py:L294-L294`, and
  `openai_scene_understanding.py:L14-L152,L326-L443,L549-L656`: provider class
  and bounded status code projection for both provider transports.
- `understanding.py:L448-L472`, `persistent_host.py:L136-L188`, and
  `single_view_perception.py:L858-L887`: allowlisted Core/runtime diagnostic
  projection with raw exception and payload exclusion.

Before/after contract diff:

```diff
- provider_route=none, provider_error_class=contract+provider_failure
+ provider_route=none
+ primary_route=qwen3-vl-4b-vllm, primary_error_class=contract,
+ primary_error_code=http_500
+ fallback_route=gpt-6.1-sol-high, fallback_error_class=provider_failure,
+ fallback_error_code=http_502
```

## Remaining operational action

The Runtime operator must inspect the Qwen service and fallback endpoint using
their deployment-owned health checks. Any credential found in persisted runtime
descriptors must be rotated and removed from future logs; this is independent of
the provider classification code and must not be printed in diagnostics.
