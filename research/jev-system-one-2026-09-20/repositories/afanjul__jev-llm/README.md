# jev-llm

A fake autoregressive language model powered by TypeSafe Jev.

Jev cannot generate text on its own. It is a judgment and classification engine. This project forces Jev into being an autoregressive language model by asking it, token by token, to pick the next piece of text from a closed inventory.

Because decisions inside one Jev call are independent, token t+1 cannot see the result of token t in the same request. That constraint forces a sequential decode loop.

https://github.com/user-attachments/assets/026fba5d-87a9-4385-89b5-c963e2f55069

## How it works

Standard language models predict a probability distribution across tens of thousands of subword tokens in a single forward pass. Jev does not have a vocabulary or a generative decode head.

Instead, each step poses a multiple-choice question to Jev:

```
next_token ~ Jev-Choice(prompt + completion, candidates <= 255)
```

1. Given what has been written so far, Jev evaluates a candidate list.
2. The candidates are sampled using a temperature parameter, or picked greedily when temperature is zero.
3. The chosen token appends to the buffer, and the loop repeats until Jev chooses `eos` or reaches the token limit.

### Generation modes

- **word** (default). Two-stage English decode. First, Jev picks either a high-frequency function word (`the`, `is`, `with`) or a starting letter bucket. If a bucket wins, a second call picks from words starting with that letter.
- **char**. Character-level decode across 26 lowercase letters, space, and punctuation. Can spell any string, but requires one Jev call per character.
- **hybrid**. Calls Jev first to plan speech act (direct answer, clarification, continuation) and target length, then decodes words until Jev signals `stop`.
- **code**. Programming mode for Python, JavaScript, and TypeScript. Uses closed inventories for keywords, builtins, standard library modules, and symbols. Includes a syntactic state machine to avoid illegal sequences (like consecutive keywords or misplaced braces) and an anti-stutter rule to stop repetitive token loops.

## Requirements

- Python 3.10+
- A TypeSafe API key from [console.typesafe.ai](https://console.typesafe.ai/settings/keys)

## Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/afanjul/jev-llm.git
cd jev-llm
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your API key:

```bash
export TYPESAFE_API_KEY="your_api_key_here"
```

## Usage

### English text generation

```bash
# Default word mode
python jev_llm.py "The capital of France is"

# Character by character decode
python jev_llm.py "Once upon a" --mode char --max-tokens 30

# Hybrid mode (plan first, then decode)
python jev_llm.py "Why is the sky blue?" --mode hybrid --max-tokens 25

# Interactive chat loop
python jev_llm.py --chat
```

### Code generation

Run with `jev_llm.py --mode code` or use the `jev_code.py` entrypoint directly.

```bash
# Python
python jev_code.py "Write a function that adds two numbers" --lang python

# JavaScript
python jev_code.py "Write a function to fetch a url and log the response" --lang javascript

# TypeScript
python jev_code.py "Write a function that returns an array of numbers" --lang typescript

# With planning step enabled
python jev_code.py "Calculate factorial recursively" --lang python --plan
```

### Interactive code chat

You can start a persistent chat session to request functions and refine code:

```bash
python jev_code.py --lang javascript --chat --temperature 0.2
```

Each turn accepts a prompt, streams the code token by token, and carries the previous code as context into the next turn.

### Options

| Flag | Default | Description |
| --- | --- | --- |
| `--mode` | `word` | Decode mode: `word`, `char`, `hybrid`, or `code` |
| `--lang` | `python` | Language for code mode: `python`, `javascript`, or `typescript` |
| `--max-tokens` | `24` (prose) / `40` (code) | Maximum tokens to decode |
| `--temperature` | `0.7` (prose) / `0.2` (code) | Sampling temperature. Use `0.0` for greedy choice |
| `--model` | `jev-1.13.0` | TypeSafe Jev model version |
| `--plan` | `False` | Run code planning step before decoding |
| `--chat` | `False` | Launch interactive terminal session |
| `--no-stream` | `False` | Disable stdout token streaming |

## Running tests

The test suite runs without making live API calls:

```bash
python -m unittest test_jev_code.py
```
