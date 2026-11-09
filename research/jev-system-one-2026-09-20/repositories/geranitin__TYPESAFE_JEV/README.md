# TYPESAFE_JEV

Experiments with [TypeSafe AI's Jev](https://typesafe.ai), a "System One" model that returns typed decisions
(choice, score, yes/no probability) with calibrated confidence instead of text.

Endpoint: `POST https://api.typesafe.ai/v1/systemone`

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then paste your TYPESAFE_API_KEY into .env
```

## Files

- `app.py` - user-upgrade triage demo; repeats the call N times to measure stability and applies confidence gating
  - `python app.py` (one call) or `python app.py 10` (ten calls, shows spread)
- `examples.py` - seven scenarios (support, agent, guardrail, resume, incident, fraud, ambiguous)
  - `python examples.py list`, `python examples.py support`, `python examples.py all`

## Question types

| type   | criteria                          | answer                          |
|--------|-----------------------------------|---------------------------------|
| choice | `{option: description or null}`   | chosen option + probabilities   |
| score  | ordered list of levels (min 2)    | weighted score + probabilities  |
| noul   | optional                          | P(yes) from 0 to 1              |

Choice and score answers also include a `confidence` value that is useful for routing uncertain cases to human review.
