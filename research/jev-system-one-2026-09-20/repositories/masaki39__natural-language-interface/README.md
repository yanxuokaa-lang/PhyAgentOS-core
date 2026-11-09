# 🗣️ nli

Turn a natural-language request into a command line. Works with gh, git, docker, kubectl, brew, aws and ~700 other CLIs.

```console
$ nli gh 'list merged pull requests'
gh pr list --state merged
$ nli docker 'composeで起動してバックグラウンドで'
docker compose up --detach
```

> [!NOTE]
> nli only **suggests** commands. Nothing runs until you press Enter yourself.

nli uses [TypeSafe Jev](https://docs.typesafe.ai/introduction), a model that picks from options instead of writing text. Every subcommand and flag it suggests exists in the tool, and a suggestion takes about 0.5 s.

## 📋 Requirements

- **Node.js** 22 or later
- **pnpm** (to install)
- **zsh** for the keybindings (the `nli` command itself works in any shell)
- **An API key** for one of:
  - [OpenRouter](https://openrouter.ai/~typesafe/jev-latest) → `OPENROUTER_API_KEY`
  - [TypeSafe](https://console.typesafe.ai/settings/keys) → `TYPESAFE_API_KEY`
- **fzf** (optional) to pick between candidates when nli is unsure

## 📦 Install

```sh
pnpm add -g https://github.com/masaki39/natural-language-interface/releases/latest/download/natural-language-interface.tgz
```

Add to `~/.zshrc`:

```sh
export OPENROUTER_API_KEY=...   # or TYPESAFE_API_KEY=...
eval "$(nli init zsh)"
```

To update: `nli update` (`nli update --check` only reports). To uninstall: `pnpm remove -g natural-language-interface`.

## 🚀 Usage

| Type at the prompt | Press | Becomes |
| --- | --- | --- |
| `nli gh リポジトリ一覧` | **Enter** | `gh repo list` |
| `gh リポジトリ一覧` | **Ctrl-X Ctrl-N** | `gh repo list` |

The line is replaced with the command. Press Enter again to run it.

You can also call nli directly:

```sh
nli <tool> <request>             # print the suggested command
nli <tool> <request> --explain   # show probabilities and timing
nli list                         # tools nli can use on this machine
nli <tool> --refresh             # re-read the tool's commands (after upgrading it)
```

## ⌨️ Keybindings

Set these in `~/.zshrc` **before** `eval "$(nli init zsh)"`:

| Variable | Default | Effect |
| --- | --- | --- |
| `NLI_KEY` | `'^X^N'` (Ctrl-X Ctrl-N) | Key that turns `<tool> <request>` into a command |
| `NLI_ENTER` | `1` | Set to `0` to make Enter on `nli ...` run it as a normal command |

> [!TIP]
> Want a single key? In vi mode (`bindkey -v`), `NLI_KEY='^N'` (Ctrl-N) is free. In emacs mode Ctrl-N is "next history", so prefer `NLI_KEY='^[n'` (Alt-N); on macOS that needs Option to act as Alt (`macos-option-as-alt = true` in Ghostty, "Use Option as Meta key" in Terminal.app, "Esc+" in iTerm2).

> [!NOTE]
> Enter only suggests for lines like `nli <tool> <request>`. Lines with options (`nli gh PR一覧 --explain`), `nli list` and every other command run as usual, and your own Enter customizations (e.g. alias expansion) keep working.

## ⚙️ How it works

1. nli reads the tool's commands once and caches them in `~/.cache/nli/specs`: from `gh help reference` for gh, from [Fig autocomplete specs](https://github.com/withfig/autocomplete) for most tools, or from `--help` for the rest.
2. Jev picks the subcommand, then the flags, from that list.
3. Values like `cli/cli` or `50` are copied from your request, never invented. Missing required arguments are shown as `<placeholders>`.

> [!IMPORTANT]
> Your request is sent to the model provider (OpenRouter or TypeSafe). Don't type secrets into it.

## 🛠️ Development

```sh
pnpm install
pnpm nli gh 'PR一覧' --explain   # run from source
pnpm eval gh                     # accuracy on eval/gh.jsonl
pnpm typecheck && pnpm build
```

Release: `pnpm release patch` (or `minor`, `major`, `X.Y.Z`; add `--dry-run` to preview). It bumps the version, then pushes a commit and a `v<version>` tag, and the tag triggers the workflow that publishes the release.
