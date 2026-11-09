# TypeSafe Jev Guardrail Connector

A UiPath Integration Service connector that lets AI Trust Layer run the `llm_as_judge`
guardrail against [TypeSafe](https://docs.typesafe.ai) Jev, a System One model that
returns calibrated probabilities instead of generated text.

Write a policy in plain language, and every agent prompt, tool call, and LLM response is
judged against it in a single sub-second model call.

> Unofficial demo project. Not a UiPath product, not supported by UiPath or TypeSafe.
> Built to explore the bring-your-own-guardrail (BYOG) extension point.

## Why Jev for this

The UiPath guardrail contract calls a connector once per guardrail check, and a judge
guardrail is a yes/no question with a threshold — which is exactly a Jev `noul`. One
request carries the whole battery, so several policies cost one round trip rather than
one each, and the response is a probability you can threshold rather than text you have
to parse.

## Prerequisites

- A UiPath tenant with bring-your-own guardrails enabled, and an org-admin user account.
- A [TypeSafe API key](https://typesafe.ai).
- `uip` CLI, logged in: `uip login` (the element key is derived from your logged-in org,
  so yours will differ from the one committed here).
- Node 18+ for the local test harness.

## The contract

Bring-your-own-guardrail needs exactly two activities.

| Activity | What it does |
|---|---|
| `GET /validators` | Returns the validator catalogue and its parameter schema. Answered locally by a `preRequest` hook with `continue: false` — no call leaves UiPath. |
| `POST /evaluate` | Takes `{validator, input, parameters[]}` and returns `{result, errorCode, details}` where `result` is `PASSED`, `FAILED`, or `ERROR`. |

## Layout

    hooks/validators-catalog.js       preRequest  GET  /validators
    hooks/evaluate-request.js         preRequest  POST /evaluate
    hooks/evaluate-verdict.js         postRequest POST /evaluate
    fields/*.json                     field schemas passed to --fields-file
    scripts/run-hooks.mjs             local harness, runs the real hook sources
    periodic-design-*/                generated connector source (uip is connectors builder)

The files under `hooks/` are the source of truth. `activity hook create` copies them into
`periodic-design-*/app/element/hooks/`, so after editing a hook, re-run the matching
`hook create` command before `validate`.

## How the policy reaches the verdict

Jev echoes each question id back as the key of its answer, and ids are never shown to the
model. So the request hook encodes the policy in the id and the response hook reads it
back off the answer:

    q__<label>__<noul|score>__<threshold x 1000, 5 digits>
    q__policy__noul__00700      fail at 70% or higher
    q__severity__score__02000   fail at severity level 2.0 or higher

No out-of-band state. The Azure Content Safety guardrail connector has to append its
thresholds to the vendor URL query string because the Azure response cannot carry them.

## Parameter mapping

The catalogue reuses the parameter ids of the UiPath built-in `llm_as_judge` validator, so
the guardrail configuration form renders the same way:

| Parameter | Jev |
|---|---|
| `guardrailText` | the `instructions` of one noul question |
| `positiveExamples` | `criteria.true.examples` |
| `negativeExamples` | `criteria.false.examples` |
| `model` | the request's `model` field |
| `threshold` | encoded in the noul question id |
| `severityBlock` | encoded in the score question id (extra, not a built-in parameter) |

## Policy shapes

`guardrailText` accepts three shapes. Each is a superset of the one below it, so an
existing single-policy guardrail is unaffected.

| Shape | Policies | Threshold | Examples | Jev calls |
|---|---|---|---|---|
| One line | 1 | the `threshold` parameter | the `positiveExamples` / `negativeExamples` parameters | 1 |
| Several lines | up to 10 | shared | **shared across every policy** | 1 |
| JSON array | up to 10 | per policy | per policy | 1 |

The flat `positiveExamples` / `negativeExamples` parameters cannot serve distinct
policies: an example that sharpens one policy misleads another. Line mode shares them
anyway, which is only safe when the policies are variations on one theme. Use the JSON
shape whenever the policies are genuinely distinct — or use separate guardrails.

```json
[
  { "id": "refunds",
    "policy": "The message promises a refund without approval.",
    "threshold": 80,
    "positive": ["I have refunded your order in full, no approval needed."],
    "negative": ["I can request a refund, but it needs manager approval."] },
  { "id": "legal",
    "policy": "The message gives legal advice.",
    "threshold": 60,
    "positive": ["You should sue them for breach of contract."] },
  { "id": "competitors",
    "policy": "The message names a competitor." }
]
```

Omitted `threshold`, `positive` and `negative` fall back to the guardrail's own
parameters. `id` reaches the verdict string (`Policy breach detected: refunds 92%.`),
is stripped to letters and digits for the question id, and is disambiguated if two ids
collide. Malformed JSON falls back to line mode rather than failing the check open.

The severity `score` question is only asked for a single policy — "how serious is the
breach" has no answer when several unrelated rules are in play.

In a coded agent, build the JSON rather than typing it:

```python
HOUSE_RULES = [
    {"id": "refunds", "policy": "...", "threshold": 80,
     "positive": ["..."], "negative": ["..."]},
    {"id": "legal", "policy": "...", "threshold": 60},
]
house_rules = ByoValidator(
    "Jev Policy Judge",
    parameters={"guardrailText": json.dumps(HOUSE_RULES)},
)
```

## Local testing

    cp .env.example .env      # paste TYPESAFE_API_KEY
    node scripts/run-hooks.mjs

Runs the real hook sources. Offline it exercises every branch of the verdict hook with
canned answer sets. With a key it posts the request hook's own body to Jev and judges the
real answers. `--offline` never calls out.

The connector itself never stores a key. The operator types it into the Integration
Service connection form, where it is held encrypted.

## Build

    uip is connectors builder validate
    uip is connectors import  --connector-dir ./periodic-design-*-typesafejevguardrails
    uip is connectors publish --connector-dir ./periodic-design-*-typesafejevguardrails --wait

Re-publishing needs a higher version: bump `latestVersion` in
`periodic-design-*/app/element/element-metadata.json` or pass `--version`.

## Register as a guardrail

    uip is connections list '<connector-key>' --all-folders --output json
    uip guardrails byo-configurations list-validators --connection-id <guid> --output json
    uip guardrails byo-configurations probe --connection-id <guid> --validator-type llm_as_judge --output json
    uip guardrails byo-configurations create --connection-id <guid> \
      --validator-name 'Jev Policy Judge' --validator-type llm_as_judge \
      --fallback-on-ui-path --output json
    uip agent guardrails list --output json

`create` always probes first: it reads the catalogue and evaluates a benign input, so a
bad key or an unreachable endpoint fails here rather than at agent runtime.

## Guardrail Connector Contract: rules the docs do not state

Found by diffing this connector against the working Azure Content Safety guardrail
connector after the platform rejected the catalogue with
`424 MALFORMED_RESPONSE: The 'validators' activity response does not conform to the
Guardrail Connector Contract`.

1. **Every parameter needs a `defaultValue`.** Registration probes the connection by
   evaluating a benign input "using the validator's default parameters", so a parameter
   with no default cannot be satisfied and the whole catalogue is rejected. This includes
   optional parameters.
2. **Parameter ids must be the ones the UiPath validator type already defines.** For
   `llm_as_judge` those are `guardrailText`, `model`, `positiveExamples`,
   `negativeExamples`, `threshold`. An id of our own invention is rejected, which is why
   the severity level is a constant in `evaluate-request.js` rather than a parameter.
3. **The field mapper drops empty arrays.** A `defaultValue: []` disappears on the way
   out and reads as a missing default, so a list default must be non-empty. A `0`
   survives, so numeric zeros are safe.
4. **Do not set a primary key on the `validators` activity.** `activity create` defaults
   one to `id` and injects a synthetic `id` field. The working connector has no primary
   key on either activity. (Removing it alone did not fix the 424 — rules 1 and 2 did —
   but it is a real divergence from the reference and makes the connector report
   `HasCruds` instead of `HasMethods`.)
5. **No `provisionAuthValidation` resource.** `validate` recommends one, and TypeSafe has
   no read-only endpoint to hang it on. The reference connector has none either, and the
   registration probe already proves the key at the moment that matters.

Verified working:

    uip guardrails byo-configurations list-validators --connection-id <guid>
      -> llm_as_judge, Status: Available
    uip guardrails byo-configurations probe --connection-id <guid> --validator-type llm_as_judge
      -> IsAvailable: true, Verdict: PASSED, 2299 ms

## Known deviations

- `validate` warns that no `provisionAuthValidation` resource exists. Deliberate: see
  contract rule 5 above.
- BYOG has no "send to a human" verdict, only `PASSED`, `FAILED`, and `ERROR`. The TypeSafe
  guardrail cookbook's review band has to collapse into the threshold at configuration
  time.
