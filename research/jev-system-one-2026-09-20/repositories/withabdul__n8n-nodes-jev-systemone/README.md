# n8n-nodes-jev-systemone

This is an n8n community node. It lets you get typed decisions from the Jev (System One) model by TypeSafe in your n8n workflows.

Jev is not a text generator. You send a `state` plus a map of typed questions (`choice`, `score`, `noul`), and get back structured `answers` with probabilities and confidence that a workflow can branch on.

[n8n](https://n8n.io/) is a [fair-code licensed](https://docs.n8n.io/sustainable-use-license/) workflow automation platform.

[Installation](#installation)
[Operations](#operations)
[Credentials](#credentials)
[Compatibility](#compatibility)
[Usage](#usage)
[Resources](#resources)
[Version history](#version-history)

## Installation

Follow the [installation guide](https://docs.n8n.io/integrations/community-nodes/installation/) in the n8n community nodes documentation.

## Operations

Evaluate — sends one request per input item and returns one item per input item, holding `model`, `answers` and `usage` merged into the input item's JSON, plus `id` and `provider` when the provider returns them.

Answer shapes per question type:

| Question type | Answer field | Kind |
| --- | --- | --- |
| `choice` | `choice` | string, one of the options sent as criteria |
| `score` | `score` | number, the rating on the scale sent as criteria |
| `noul` | `noul` | number between 0 and 1, how likely the answer is true |

`probabilities`, `confidence` and `legend` come back when the provider sends them. They are never required and never filled in with made-up values.

## Credentials

The node reaches the same model through two providers. Pick the provider in the **Provider** parameter, then create the matching credential.

**TypeSafe Jev API** — an API key from the TypeSafe console. Requests go to `POST {Base URL}/v1/systemone` with `Authorization: Bearer <key>`. The default Base URL is `https://api.typesafe.ai`.

**OpenRouter API** — an API key from the OpenRouter dashboard. Requests go to `POST {Base URL}/v1/systemone` with `Authorization: Bearer <key>`. The default Base URL is `https://openrouter.ai/api`.

Both credential types have a **Base URL** field so a proxy, gateway or self-hosted endpoint can be used instead. Saving a credential runs a live check against the provider (`GET /v1/models` for TypeSafe, `GET /v1/key` for OpenRouter), so an invalid key is reported at save time.

## Compatibility

Built with `@n8n/node-cli` and compiled against the `n8n-workflow` node API version 1.

## Usage

Send a state and the questions to ask about it:

- **State** — a text string, or a JSON object/array. The questions are evaluated against it.
- **Questions Input** — `Form` builds each question from fields; `JSON` takes the whole questions map as an object and passes it through as written. JSON mode is the only way to send `instructions` or `criteria` as an object or array.
- **Model** — `jev-latest` works on both providers. Versioned IDs such as `jev-1.13.0` (TypeSafe) or `typesafe/jev-1.13` (OpenRouter) also work.
- **Options → Timeout** — request timeout in milliseconds, 60000 by default.

Example payload for the state `{"ticket":"My checkout page shows a blank screen after I click Pay."}` with a `choice` question `department` (`payments`, `frontend`), a `score` question `urgency` (`Can wait`, `This week`, `Blocking revenue`) and a `noul` question `is_bug`:

```json
{
  "model": "jev-latest",
  "state": { "ticket": "My checkout page shows a blank screen after I click Pay." },
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this ticket?",
      "criteria": {
        "payments": "Checkout, billing, payment issues",
        "frontend": "Rendering or browser issues"
      }
    },
    "urgency": {
      "type": "score",
      "instructions": "How urgent is this ticket?",
      "criteria": ["Can wait", "This week", "Blocking revenue"]
    },
    "is_bug": {
      "type": "noul",
      "instructions": "Does this message report broken behavior?",
      "criteria": { "true": "Broken behavior", "false": "Question or feature request" }
    }
  }
}
```

The returned item keeps the input item's fields and adds the answers:

```json
{
  "ticket": "My checkout page shows a blank screen after I click Pay.",
  "model": "jev-1.13.0",
  "answers": {
    "department": { "type": "choice", "choice": "payments", "probabilities": { "payments": 0.84, "frontend": 0.16 }, "confidence": 0.75 },
    "urgency": { "type": "score", "score": 1.99, "probabilities": { "0": 0, "1": 0.01, "2": 0.99 }, "confidence": 0.99 },
    "is_bug": { "type": "noul", "noul": 0.96 }
  },
  "usage": { "input_tokens": 318, "output_tokens": 34 }
}
```

Enable **Continue On Fail** to let the workflow proceed with an `error` field on the item instead of failing the run.

## Resources

* [n8n community nodes documentation](https://docs.n8n.io/integrations/#community-nodes)
* [TypeSafe API documentation](https://docs.typesafe.ai/api)
* [OpenRouter TypeSafe SDK guide](https://openrouter.ai/docs/guides/community/typesafe-sdk)

## Version history

### 0.1.0

Initial release with the Evaluate operation.