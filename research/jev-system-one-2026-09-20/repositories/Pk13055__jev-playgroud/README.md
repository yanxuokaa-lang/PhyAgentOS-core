# jev-dev

A small CLI for asking [TypeSafe](https://docs.typesafe.ai)'s Jev model a typed question: yes/no (`noul`), pick-one (`choice`), or graded (`score`).

## Setup

1. Install [uv](https://docs.astral.sh/uv/) and Python 3.13+.
2. From this directory:

   ```bash
   uv sync
   ```

3. Put your TypeSafe API key in the environment, or in a `.env` file next to `jev.py`:

   ```bash
   TYPESAFE_API_KEY=your_key_here
   ```

   Create a key at [console.typesafe.ai](https://console.typesafe.ai).

`./jev.py` uses `uv run`, so you can call it directly after that.

## Usage

```bash
./jev.py -m <noul|choice|score> -q "<question>" [-s "" | -s "context" | -s /path/to/file] [--choices a,b,c]
```

| Flag | Meaning |
| --- | --- |
| `-m` / `--mode` | Question type: `noul`, `choice` (`choices` also works), or `score` |
| `-q` / `--query` | The question to ask |
| `-s` / `--state` / `-i` | State: empty string, inline text, or a path to a text file |
| `--choices` | Required for `choice` (option labels) and `score` (ordered levels), comma-separated |

Answers print as JSON.

If `-s` is an existing file path, the file is read and sent as state. Otherwise the string is sent as-is. `-s ""` means no extra context.

## Examples

Captured from live Jev calls. A noul is the probability of yes (near 1 = yes, near 0 = no). A choice returns the selected option plus probabilities. A score is a position on your ordered levels (0 is the first level).

### Noul (yes/no)

World knowledge, no extra context:

```bash
./jev.py -m noul -q "Is the sky typically blue during a clear day?" -s ""
```

```json
{
  "type": "noul",
  "noul": 0.98
}
```

```bash
./jev.py -m noul -q "Is 2 + 2 equal to 5?" -s ""
```

```json
{
  "type": "noul",
  "noul": 0.01
}
```

Judge a short snippet:

```bash
./jev.py -m noul -q "Does the customer request a refund?" -s "I was charged twice. Please send my money back."
```

```json
{
  "type": "noul",
  "noul": 0.98
}
```

```bash
./jev.py -m noul -q "Does this resume mention Python?" -s "Built backend services in Go and Rust for five years."
```

```json
{
  "type": "noul",
  "noul": 0.01
}
```

### Choice (pick one)

Tone:

```bash
./jev.py -m choice --choices calm,frustrated,angry -q "What is the customer's tone?" -s "I was charged twice. Please fix this ASAP."
```

```json
{
  "type": "choice",
  "choice": "frustrated",
  "confidence": 0.75,
  "probabilities": {
    "calm": 0.0,
    "angry": 0.17,
    "frustrated": 0.83
  }
}
```

Language of a snippet:

```bash
./jev.py -m choice --choices python,javascript,rust,go -q "Which programming language is this snippet written in?" -s "def greet(name): return f'Hello {name}'"
```

```json
{
  "type": "choice",
  "choice": "python",
  "confidence": 1.0,
  "probabilities": {
    "python": 1.0,
    "javascript": 0.0,
    "go": 0.0,
    "rust": 0.0
  }
}
```

Routing:

```bash
./jev.py -m choice --choices billing,technical,sales,other -q "Which team should handle this request?" -s "My API keys stopped working after yesterday's deploy."
```

```json
{
  "type": "choice",
  "choice": "technical",
  "confidence": 1.0,
  "probabilities": {
    "billing": 0.0,
    "other": 0.0,
    "sales": 0.0,
    "technical": 1.0
  }
}
```

Sentiment:

```bash
./jev.py -m choice --choices positive,negative,neutral -q "What is the overall sentiment?" -s "The food was okay, nothing special."
```

```json
{
  "type": "choice",
  "choice": "neutral",
  "confidence": 0.99,
  "probabilities": {
    "neutral": 1.0,
    "negative": 0.0,
    "positive": 0.0
  }
}
```

### Score (rating)

Urgency:

```bash
./jev.py -m score --choices "can wait,this week,today" -q "How urgent is this ticket?" -s "Production is down. Customers cannot log in."
```

```json
{
  "type": "score",
  "score": 2.0,
  "confidence": 1.0,
  "legend": {
    "0": "can wait",
    "1": "this week",
    "2": "today"
  },
  "probabilities": {
    "0": 0.0,
    "1": 0.0,
    "2": 1.0
  }
}
```

Frustration (polite request → calm):

```bash
./jev.py -m score --choices "calm,concerned,very angry" -q "How frustrated does the customer appear?" -s "Hi, when you have a moment could you look at my invoice?"
```

```json
{
  "type": "score",
  "score": 0.0,
  "confidence": 0.99,
  "legend": {
    "0": "calm",
    "1": "concerned",
    "2": "very angry"
  },
  "probabilities": {
    "0": 1.0,
    "1": 0.0,
    "2": 0.0
  }
}
```

Skill level:

```bash
./jev.py -m score --choices "no experience,some familiarity,daily use,deep expertise" -q "What is this candidate's Python skill level?" -s "I have used Python in production for eight years, including asyncio internals."
```

```json
{
  "type": "score",
  "score": 3.0,
  "confidence": 1.0,
  "legend": {
    "0": "no experience",
    "1": "some familiarity",
    "2": "daily use",
    "3": "deep expertise"
  },
  "probabilities": {
    "0": 0.0,
    "1": 0.0,
    "2": 0.0,
    "3": 1.0
  }
}
```

Spamminess:

```bash
./jev.py -m score --choices "legitimate,slightly promotional,obvious spam" -q "How spam-like is this message?" -s "CONGRATULATIONS YOU WON $1,000,000 CLICK HERE NOW"
```

```json
{
  "type": "score",
  "score": 2.0,
  "confidence": 1.0,
  "legend": {
    "0": "legitimate",
    "1": "slightly promotional",
    "2": "obvious spam"
  },
  "probabilities": {
    "0": 0.0,
    "1": 0.0,
    "2": 1.0
  }
}
```

### Financial Use Cases

Accounting, credit, and investment banking judgments on short snippets.

Duplicate payment (AP):

```bash
./jev.py -m noul -q "Does this look like a request to pay an invoice that was already paid?" -s "Vendor Acme sent invoice 4419 for $18,400 on March 3. AP already paid invoice 4419 on March 5. The vendor emailed again asking when they will be paid."
```

```json
{
  "type": "noul",
  "noul": 0.97
}
```

Earnings vs consensus:

```bash
./jev.py -m noul -q "Did this company miss consensus earnings per share?" -s "Q3 EPS came in at $1.12 versus consensus of $1.31. Revenue was in line with estimates."
```

```json
{
  "type": "noul",
  "noul": 0.98
}
```

Cash-flow classification:

```bash
./jev.py -m choice --choices operating,investing,financing -q "How should this cash outflow be classified on the cash flow statement?" -s "The company paid $40 million to acquire a warehouse and the land under it."
```

```json
{
  "type": "choice",
  "choice": "investing",
  "confidence": 1.0,
  "probabilities": {
    "investing": 1.0,
    "operating": 0.0,
    "financing": 0.0
  }
}
```

Investment banking product:

```bash
./jev.py -m choice --choices ma_advisory,ecm,dcm,leveraged_finance,other -q "Which investment banking product does this client request describe?" -s "We want to raise $500 million of senior unsecured notes to refinance the 2027 maturity and fund a small bolt-on."
```

```json
{
  "type": "choice",
  "choice": "dcm",
  "confidence": 0.99,
  "probabilities": {
    "leveraged_finance": 0.0,
    "ecm": 0.0,
    "dcm": 1.0,
    "ma_advisory": 0.0,
    "other": 0.0
  }
}
```

Borrower credit risk (score can land between levels):

```bash
./jev.py -m score --choices "low,moderate,elevated,severe" -q "How severe is this borrower's credit risk?" -s "Leverage is 6.8x EBITDA, interest coverage is 1.3x, and cash has declined for three quarters. The revolver is 90% drawn."
```

```json
{
  "type": "score",
  "score": 2.73,
  "confidence": 0.73,
  "legend": {
    "0": "low",
    "1": "moderate",
    "2": "elevated",
    "3": "severe"
  },
  "probabilities": {
    "0": 0.0,
    "1": 0.0,
    "2": 0.27,
    "3": 0.73
  }
}
```

Quality of earnings:

```bash
./jev.py -m score --choices "low quality,mixed,high quality" -q "How high is the quality of these reported earnings?" -s "Operating cash flow was $12 million while net income was $48 million. Most of the gap is an increase in receivables and a one-time gain on a building sale."
```

```json
{
  "type": "score",
  "score": 0.03,
  "confidence": 0.95,
  "legend": {
    "0": "low quality",
    "1": "mixed",
    "2": "high quality"
  },
  "probabilities": {
    "0": 0.97,
    "1": 0.03,
    "2": 0.0
  }
}
```
