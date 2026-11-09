# siftr

**Find the right code without reading the whole codebase.** siftr gives AI coding agents
(and you) four read-only tools that answer "where is it?" and "which part matters?" in about
a second, for about a cent — so agents spend their tokens on the work, not on searching.

```console
$ siftr "where are users charged credits when a block runs"
0.83  backend/backend/executor/billing.py:114-193
      def charge_usage(
0.81  backend/backend/copilot/tools/helpers.py:439-518
      # still settles billing via asyncio.shield — external side effects
```

## Benchmark results

Measured on [SWE-bench Lite](https://www.swebench.com/) — 300 real GitHub issues from 12
Python projects, where we know which file and lines the real fix changed. Numbers are from
a **frozen test split of 202 issues** that siftr was never tuned on.

| Tool | Question it answers | siftr | Best baseline |
|---|---|---|---|
| `search` | Which file does this issue need changed? *(right file in top 5)* | **82%** | BM25 52% · grep 22% |
| `read` | Which parts of this file matter? *(edited lines kept · file cut)* | **92% · 59% cut** | simple cut-off: 67% · 75% cut |
| `pick` | Which of ~550 test files covers this? *(right file in top 5)* | **81%** | BM25 38% |
| `filter` | Which parts of this long log matter? | experimental | grep wins on keyword logs |

- **Speed:** search takes ~2s on a 4,000-file repo (p90 2.9s); read and pick take under half a second.
- **Cost:** 1–2¢ per search on a large repo; read and pick cost well under a cent.
- **Where it doesn't win:** if you already know the exact words, use grep — it's instant
  and free. `filter` lost to grep on the one labelled log dataset available, so it's
  marked experimental.

Full method, per-project results, and the ideas that *didn't* work: **[BENCHMARKS.md](BENCHMARKS.md)**.

## Install

```bash
# macOS / Linux
curl -LsSf https://raw.githubusercontent.com/Bentlybro/siftr/main/install.sh | sh
# Windows (PowerShell)
irm https://raw.githubusercontent.com/Bentlybro/siftr/main/install.ps1 | iex
```

Nothing needs to be installed first — the script brings its own Python via
[uv](https://docs.astral.sh/uv). Then, once:

```bash
siftr setup             # paste an OpenRouter API key (openrouter.ai/settings/keys)
siftr agents install    # add siftr to your coding agents
```

## Use it with AI agents

`siftr agents install` finds your coding agents and adds siftr as an MCP server — **Claude
Code, Codex, Cursor, Claude Desktop, Gemini CLI, Windsurf, Kiro, opencode, pi and omp**.
It backs up each config file first, leaves your other servers alone, and is safe to re-run.

The agent gets four tools:

| MCP tool | The agent uses it when… |
|---|---|
| `semantic_search` | it doesn't know the names of what it's looking for |
| `focused_read` | it needs one part of a large file, not the whole thing |
| `pick_relevant` | it has a long list (tests, docs, files) and needs the few that matter |
| `filter_output` | a log on disk is too long to read *(experimental)* |

Manual setup for any other client, and a snippet that tells your agent when to use these:
**[docs/agents.md](docs/agents.md)**.

## Use it yourself

```bash
siftr "how does the frontend decide whether to show onboarding"     # search this folder
siftr search "code that retries failed HTTP calls" ~/src/project    # search another folder
siftr read src/billing.py "where is the refund amount calculated"   # just the relevant parts
git ls-files 'tests/*.py' | siftr pick "fix the login redirect bug" -n 10
pytest -x 2>&1 | siftr filter "why does test_login fail"           # experimental
```

Every command takes `--json`; `search` takes `--stats` for time and cost, and `-h` lists
the rest.

## How it works

siftr runs on [TypeSafe Jev](https://typesafe.ai), a *decision* model: instead of writing
text, it answers yes/no questions with a probability. Every siftr tool asks the same kind of
question — "is this relevant?" — about many pieces of text at once:

1. **Hundreds of questions per request.** Asking about 300 files takes 0.50s; asking about
   one takes 0.36s.
2. **All requests at once.** A 4,000-file repo becomes a few dozen parallel requests —
   0.9s, versus ~23 minutes checking one file at a time.
3. **No waiting on stragglers.** A request that hasn't answered after 2s gets a duplicate;
   whichever finishes first wins.
4. **Two passes for search.** First rank every file from its name and definitions, then
   zoom into the best 30 files to point at exact lines.

Each tool, step by step, with diagrams: **[docs/how-it-works.md](docs/how-it-works.md)**.

## Safe for agents by design

siftr only **suggests**; it never deletes or rewrites anything in the agent's context:

- `read` lists every section it left out, and `filter` keeps the full output on disk.
- A wrong answer costs one extra read, never lost information.
- Every tool tells the agent to fall back to grep or a full read if nothing fits.

## Privacy and cost

Each call sends file paths, definition names and relevant snippets to OpenRouter, which
routes them to TypeSafe. **Don't use it on code you can't send to a third-party API.**
Pricing is $0.042 per million input tokens — a large-repo search costs 1–2¢.

## Development

```bash
python -m unittest discover -s tests -t .     # offline tests, no key needed
python bench/swebench.py run all              # search benchmark (needs a key)
python bench/swebench_tools.py read test      # read / pick benchmarks
```

MIT licensed.
