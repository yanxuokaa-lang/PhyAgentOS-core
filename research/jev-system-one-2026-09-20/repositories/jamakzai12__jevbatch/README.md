# jevbatch

Score CSV or JSONL rows with [TypeSafe Jev](https://typesafe.ai) — typed questions, calibrated confidence, and **auto / review / escalate** (or **post / rewrite / block**) routes from a YAML policy.

Jev is a System One model: unstructured state in → Choice / Score / Noul out. `jevbatch` is the data-plane CLI that makes that usable on files.

## Install

```bash
git clone https://github.com/jamakzai12/jevbatch.git
cd jevbatch
pip install -e .
# development extras (pytest):
pip install -e ".[dev]"
```

Once published: `pip install jevbatch`.

Requires **Python 3.10+**.

## Configure

Get an API key from the [TypeSafe console](https://console.typesafe.ai/keys) and set it in the environment. **Never commit `.env` or real keys.**

```bash
export TYPESAFE_API_KEY=your_key_here
# or: cp .env.example .env  &&  edit .env  (gitignored)
```

`.env.example` is a placeholder only:

```
TYPESAFE_API_KEY=your_key_here
```

## Quick start

```bash
jevbatch --help

jevbatch run examples/data/sample_tickets.csv \
  -p examples/policies/tickets.yaml \
  -o scored.json

jevbatch run examples/data/sample_replies.csv \
  -p examples/policies/replies.yaml

jevbatch policies
```

JSONL works the same way (`*.jsonl` / ndjson). Use `-n 5` to score a prefix of the file.

## How it works

1. Each row becomes Jev **state** (a text field, or a dict of `state_fields` plus optional `brand`).
2. The YAML **policy** defines parallel questions (`choice`, `score`, `noul`).
3. Answers become metrics (`urgency`, `spam`, `confidence`, …).
4. The first matching **route** expression wins (`eval` against those floats; policies are trusted local files).

Wire this into outreach / support / social agents: only ship rows that route to `auto` or `post`.

## Example policy sketch

```yaml
name: support-tickets
model: jev-latest
state_field: text
questions:
  is_urgent:
    type: noul
    instructions: The message conveys urgency
routes:
  - when: "confidence < 0.45"
    route: review
  - when: "urgency >= 0.85"
    route: escalate
  - when: "true"
    route: auto
```

Bundled examples:

| File | Role |
| --- | --- |
| `examples/policies/tickets.yaml` | Support tickets → `auto` / `review` / `escalate` |
| `examples/policies/replies.yaml` | Social drafts → `post` / `rewrite` / `block` |
| `examples/data/sample_tickets.csv` | Ticket rows (`id`, `text`) |
| `examples/data/sample_replies.csv` | Reply drafts (`id`, `platform`, `draft`) |

## CLI

| Command | Purpose |
| --- | --- |
| `jevbatch run DATA -p POLICY [-o OUT] [-n N]` | Score each row and write JSON |
| `jevbatch policies` | List YAML files under `examples/policies` |

Default output (when `-o` is omitted) is `data/scored_<policy-name>.json` at the project root.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests mock `TypeSafeClient` and **do not** call the live TypeSafe API. Do not put real keys in the tree; CI and local pytest only need the placeholder env pattern.

## License

MIT — see [LICENSE](LICENSE).
