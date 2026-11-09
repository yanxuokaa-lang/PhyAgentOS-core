<img width="943" height="566" alt="image" src="https://github.com/user-attachments/assets/def49d8b-2ef4-4265-ac6a-c0520ff75059" />


# jev-preview

**A TUI — a full-screen, keyboard-driven terminal application — for the
[TypeSafe](https://docs.typesafe.ai) System One API**
(`POST https://api.typesafe.ai/v1/systemone`).

It is not a command-line tool that prints and exits: running `jev-preview` takes over
your terminal with three live panes. You write a context, build the questions in a form
rather than by hand, press <kbd>enter</kbd> to send, and read the answers as probability
bars instead of raw JSON. Everything is driven by single keystrokes — vim-style
`h` `j` `k` `l` to move between panes, `e` to edit the focused one, `q` to quit — and
there are no subcommands to learn.

```
┌─ context ──────────┬─ response ─────────┐
│  the `state` you   │  answers, rendered │
│  send   (1/3)      │  with probability  │
├─ questions ────────┤  bars, then the    │
│  the `questions`   │  raw JSON          │
│  map, as a form    │                    │
│         (2/3)      │                    │
└────────────────────┴────────────────────┘
```

Every request you work on is saved as a JSON file holding its name, creation date,
request body, and the full history of responses it has received, so the sandbox
remembers what you tried and what came back.

Built with [Textual](https://textual.textualize.io/). It needs a real terminal —
any modern one will do (kitty, Alacritty, WezTerm, iTerm2, Windows Terminal, tmux) —
and does not work through a pipe or in a non-interactive shell. The small handful of
things that *are* plain command-line flags (`--set-key`, `--show-config`, `--version`)
are listed below and never open the interface.

## Install

**Arch Linux** — from the [AUR](https://aur.archlinux.org/packages/jev-preview), with
any helper:

```sh
paru -S jev-preview          # or: yay -S jev-preview
```

**macOS and Linux** — from the Homebrew tap:

```sh
brew install arkadyburyakov/tap/jev-preview
```

**Anywhere with Python 3.11+** — from [PyPI](https://pypi.org/project/jev-preview/):

```sh
pipx install jev-preview     # or: uv tool install jev-preview
```

Then:

```sh
jev-preview                  # launches the TUI
```

Both `jev-preview` and the shorter `jev` start the same application.

To install from a clone of this repository instead, run `uv tool install .` (or
`pipx install .`) from its root.

The first run opens the TUI and asks for your TypeSafe API key, storing it in your
user config directory (`~/.config/jev-preview/config.json` on Linux), readable only
by you. Declining the prompt exits without writing anything. Press
<kbd>ctrl</kbd>+<kbd>k</kbd> at any time to change it.

To set the key from the shell instead, without opening the TUI:

```sh
jev-preview --set-key sk-…
pbpaste | jev-preview --set-key -     # or read it from stdin
jev-preview --show-config             # where everything lives
```

`TYPESAFE_API_KEY` is honoured if you would rather keep the key in your environment;
it wins over the config file and is never written to disk.

## Keys

### Normal mode

| key | action |
| --- | --- |
| `h` `j` `k` `l` or arrows | move between panes |
| `e` | edit the focused pane here |
| `E` | edit it in `$EDITOR` instead |
| `enter` | send the request |
| `[` / `]` | previous / next response in history |
| `o` | open the requests catalogue |
| `n` | start a new, empty request |
| `c` | copy the current request (context + questions, no response history) |
| `r` | rename the current request |
| `d` | delete the current request |
| `m` | cycle model (`jev-latest` → `jev-preview` → `jev-1.13.0`) |
| `ctrl+k` | change the API key |
| `?` | help |
| `q` | quit |

In the response pane, `j`/`k` scroll (there is no pane above or below it), `g`/`G` jump
to top and bottom, and `pgup`/`pgdn` page through. In the catalogue, typing filters by
name or filename, and `ctrl+d` deletes the highlighted request after a confirmation.

### Edit mode

`e` opens the focused pane for editing; `esc` returns to normal mode and saves. The
border turns green and the title gains a `✎ esc` marker.

**context** is a plain text buffer: every key types, arrows move the cursor, `enter`
inserts a newline.

**questions** is a form, not a text buffer. Each question is a card with an id field, a
type dropdown, an instructions box, and criteria widgets that follow the type — so the
structure is chosen, and only free text is typed:

| type | criteria |
| --- | --- |
| `noul` | optional descriptions of what *true* and *false* mean |
| `choice` | option rows: a name and an optional description, `+ option` to add |
| `score` | ordered level rows, numbered as the API reports them, `+ level` to add |

`tab`/`shift+tab` and the arrow keys both cycle the fields, and stay inside the form;
`enter` or `space` activates a button, including opening the type dropdown. `+ question`
appends a card and `✕ remove` deletes one. Switching type keeps what the other types
held, so flipping `choice → score → choice` loses nothing.

Pressing `e` with no questions yet starts one for you, with its generated id selected so
typing renames it; leaving with `esc` before filling anything in discards it again.

Problems are reported live — a missing id, a duplicate id, absent instructions, a choice
with fewer than two options, a score with fewer than two levels — in the pane title and
under the summary, and `enter` refuses to send until they are gone.

`ctrl+h/j/k/l` are deliberately unbound, so they pass straight through to a
terminal-level splits navigator (kitty's `pass_keys.py`, tmux, and friends) and still
move you between terminal windows from inside jev.

## Editing the panes

Edits are written to disk when you leave edit mode, about a second and a half after you
stop typing, and again on send and on quit — there is no explicit save.

**context** is the request's `state`. It is plain text, and stays plain text unless what
you type parses as a JSON object or array — so both `a support ticket like this` and a
structured chat log work.

**questions** is the `questions` map. The form covers the documented shapes; a question
using the [advanced structure](https://docs.typesafe.ai/primitives/advanced) the API
also accepts — an object or array for `instructions`, say — is shown read-only and
carried through byte-for-byte rather than flattened. Edit those with `E`.

`E` hands the focused pane to `$EDITOR`: the raw text for context, the raw `questions`
JSON for questions. If that JSON does not parse, it is kept verbatim in the file as
`draft_questions` — the form refuses to open over it, and `E` reopens your text to fix.

The three question types (see [primitives](https://docs.typesafe.ai/primitives)):

```json
{
  "is_urgent":   { "type": "noul",   "instructions": "Does this convey urgency?" },
  "department":  { "type": "choice", "instructions": "Which team should handle this?",
                   "criteria": { "billing": "Payments", "technical": "Bugs", "sales": "Pricing" } },
  "frustration": { "type": "score",  "instructions": "How frustrated is the customer?",
                   "criteria": ["Calm", "Frustrated", "Very angry"] }
}
```

## Naming

A new request names itself after the first line of its context and keeps following it,
renaming its file as you go (`auto_name: true` in the file). `r` gives it a real name,
which pins both the name and the filename from then on. A copy is born with the pinned
name `Copy of …`.

## Where things are stored

| what | where | override |
| --- | --- | --- |
| config (API key, base URL, models) | `~/.config/jev-preview/config.json` | `JEV_CONFIG_DIR` |
| saved requests | `~/.local/share/jev-preview/requests/` | `JEV_REQUESTS_DIR`, `--requests-dir` |

macOS and Windows get their own platform-appropriate locations via
[platformdirs](https://pypi.org/project/platformdirs/). The config file is written with
`0600` permissions; a key taken from `TYPESAFE_API_KEY` is never written at all.

```json
{
  "api_key": "sk-…",
  "base_url": "https://api.typesafe.ai/v1",
  "models": ["jev-latest", "jev-preview", "jev-1.13.0"],
  "timeout": 60.0
}
```

Everything but `api_key` is optional; edit the file to point at a different deployment
or to change the models `m` cycles through.

### Saved request format

```json
{
  "name": "Help! My payouts have been failing",
  "created_at": "2026-09-17T15:02:45+00:00",
  "auto_name": true,
  "body": { "model": "jev-latest", "state": "...", "questions": {} },
  "responses": [
    { "timestamp": "...", "status": 200, "duration_ms": 979, "body": {} }
  ]
}
```

`auto_name` is present only while the name tracks the context, and `draft_questions`
only while the questions buffer does not parse.

## Development

```sh
uv sync                                  # install with dev dependencies
uv run pytest                            # unit + end-to-end tests
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run textual run --dev jev_preview.app:JevApp   # with the Textual devtools console
```

Tests drive the real TUI through Textual's `Pilot`, with HTTP mocked by `respx`, and
never touch your own config or saved requests — `conftest.py` redirects both to a
temporary directory.

### Releasing

A release is one commit to `main`: bump `__version__` in
`src/jev_preview/__init__.py` and add that version's section to
[CHANGELOG.md](CHANGELOG.md). `pyproject.toml` has no version of its own —
hatchling reads it from `__init__.py`, so the two can never disagree.

On push, `release.yml` tags `v<version>` and creates the GitHub release with that
changelog section as its notes. Publishing to the three channels then happens on
`release: published`, in parallel and independently:

| workflow | channel | built from |
| --- | --- | --- |
| `publish_pypi.yml` | [PyPI](https://pypi.org/project/jev-preview/) | the sdist and wheel, trusted publishing — no token |
| `publish_aur.yml` | [AUR](https://aur.archlinux.org/packages/jev-preview) | `packaging/AUR/PKGBUILD.template` |
| `publish_homebrew.yml` | the `arkadyburyakov/tap` tap | `packaging/homebrew/jev-preview.rb.template` |

Each renders its template with the version and the release tarball's checksum,
builds the package, and runs `packaging/smoke-test` against the *installed* result —
which starts the TUI headless, so a package that installed without `app.tcss`, or
against a `textual` too old, fails before it is published. Nothing is committed back
to this repository; the rendered PKGBUILD and formula exist only inside the workflow
run and in the AUR and tap repositories.

Changing the runtime dependencies in `pyproject.toml` means updating both packaging
templates: the Arch `depends=()` array, and the Homebrew formula's pinned `resource`
blocks (regenerate those with `brew update-python-resources` against the rendered
formula).

## License

MIT — see [LICENSE](LICENSE).
