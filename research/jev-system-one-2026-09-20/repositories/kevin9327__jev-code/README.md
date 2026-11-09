<p align="center">
  <img src="https://img.shields.io/badge/model-jev--latest-14b8a6" alt="jev-latest">
  <img src="https://img.shields.io/badge/POST-api.typesafe.ai%2Fv1%2Fsystemone-0f766e" alt="System One endpoint">
  <img src="https://img.shields.io/badge/gate-merge%20%7C%20comment%20%7C%20block-134e4a" alt="merge comment block">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-5eead4" alt="MIT">
  <img src="https://img.shields.io/badge/not-Copilot-1f2937" alt="Not Copilot">
  <img src="https://img.shields.io/badge/not-a%20code%20generator-111827" alt="Not a code generator">
</p>

<p align="center"><b>Diff in. Typed answers out. Code opens or closes the merge.</b><br>
<code>POST /v1/systemone</code> · <code>jev-latest</code> · Choice + Score + Noul in one call · <code>merge</code> / <code>comment</code> / <code>block</code> in Python.</p>

# JevCode

**A diff merge gate, not a code generator, not Copilot, not DocAgent.**

Jev is TypeSafe's [System One](https://docs.typesafe.ai/concepts/system-one) model: send a *state* and typed *questions*, get structured *answers* your program can branch on. In this repo the state is a **unified diff** (or patch text). One mixed Jev call returns:

| Question | Primitive | Returns |
| --- | --- | --- |
| `review` | **Choice** | `approve` \| `comment` \| `request_changes` |
| `risk` | **Score** | 4 levels — cosmetic / local / cross-cutting / security-sensitive |
| `tests_missing` | **Noul** | probability that "this change needs tests that are not in the diff" |

`compose_review_gate` is ordinary Python. Jev does not merge the PR.

Sibling north-star repo: [kevin9327/jev-master](https://github.com/kevin9327/jev-master).

## Why this exists

Chat models generate patches and review essays. A merge gate needs a bounded decision: *merge, comment, or block?* Parsing a paragraph is the wrong interface.

```
unified diff  -->  POST https://api.typesafe.ai/v1/systemone  (model: jev-latest)
                   typed answers (no prose)
                   -->  compose_review_gate(answers) in this repo
                   -->  gate: merge | comment | block
```

The HTTP client is injectable. Tests feed real-shaped answers without hitting the network.

## Gate rules (code, not a prompt)

- `review.choice == request_changes` **or** `risk.score >= 2.5` **or** `tests_missing.noul >= 0.75` → **block**
- `review.choice == comment` **or** `risk.score >= 1.2` → **comment**
- else → **merge**
- `review.confidence < 0.5` → **block**

If the policy changes, change a threshold — do not rewrite a prompt.

## Quickstart

Python 3.10+. Get a TypeSafe key from the [dashboard](https://console.typesafe.ai/settings/keys) and export it as `TYPESAFE_API_KEY` (never commit it). On this machine the loader also accepts `C:\Users\swsz9\Downloads\jevkey.txt`.

```bash
git clone https://github.com/kevin9327/jev-code
cd jev-code
python -m pip install -e ".[dev]"
python -m pytest
python -m jevcode --state examples/risky.diff
```

That command prints JSON with typed `answers` plus a composed `decision` (`gate` + `review` + `risk` + `tests_missing`).

```bash
python -m jevcode --state examples/safe.diff    # docs / typo
python -m jevcode --state examples/risky.diff   # auth SQL + deleted tests
```

## Examples

| File | What it is |
| --- | --- |
| [`examples/safe.diff`](examples/safe.diff) | Typo / docs change |
| [`examples/risky.diff`](examples/risky.diff) | Auth query string-interpolated; tests deleted |

## Secrets

The API key is runtime-only. This tree gitignores `.env`, `jevkey.txt`, `apikey_*`, and `.venv`. Do not paste keys into README, tests, or CI logs.

## License

MIT. See [LICENSE](LICENSE).
