# joxide

Jump to projects by description, powered by zoxide and TypeSafe’s Jev.

Zoxide maintains the directory index; Jev ranks known directories when a name match is not enough.

```zsh
j auth backend
j cloudflare experiment
j yesterday
j the frontend I worked on yesterday
```

This is a small zsh integration, with no Oh My Zsh, plugin manager, fzf, or background daemon required. Existing `z` commands continue to work.

## Installation

### Quick install

With Git, Node.js, npm, and zoxide installed, run:

```zsh
git clone https://github.com/ant4g0nist/joxide.git "$HOME/.joxide" && npm --prefix "$HOME/.joxide" ci --omit=dev --ignore-scripts
```

Add this line to `~/.zshrc` after your other shell integrations, then run the same line in your current zsh terminal:

```zsh
source "$HOME/.joxide/joxide.plugin.zsh"
```

This enables `j` and `jctl`. The checkout must stay at that path; if you choose another location, update the source line to match.

### Prerequisites

Use zsh on macOS or Linux, with [Node.js](https://nodejs.org/en/download) 22.18+ on the 22.x line, or 24+, and [zoxide](https://github.com/ajeetdsouza/zoxide#installation). Node runs the TypeScript source directly; no build step is needed.

On macOS with Homebrew, install any missing tools:

```zsh
brew install git node zoxide
```

On Linux, install Git and zsh through your distribution's package manager, then follow the Node.js and zoxide installation guides linked above. Run the source command from an interactive zsh shell.

### Enable semantic search

Get a key following the [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart), then add this to `~/.zshrc` before the joxide source line, replacing the placeholder:

```zsh
export TYPESAFE_API_KEY='your-typesafe-api-key'
```

Open a new terminal to load the setting. Exact paths, directory-name matching, and bare date queries work locally without a key. Semantic queries send project metadata to the TypeSafe API and use your account quota; see [Data and configuration](#data-and-configuration).

### Add your projects

Replace `~/projects` with an existing folder containing your repositories:

```zsh
jctl index ~/projects
jctl doctor
j --local my-project
```

Replace `my-project` with one of your directory names. You can then try a description such as `j auth backend`. Normal `cd` use grows the index automatically. Date-based history starts when joxide is loaded.

If `jctl` is not found, run the source line again in zsh. If `jctl doctor` reports a missing executable, make sure `node` and `zoxide` are on your `PATH`, or configure `JOXIDE_NODE` and `JOXIDE_ZOXIDE` before sourcing.

## Everyday use

| Command | Behavior |
| --- | --- |
| `j api` | Match known directory names locally |
| `j auth backend` | Fall back to semantic matching when names do not match |
| `j --semantic auth backend` | Force semantic ranking even if a name matches |
| `j yesterday` | Choose from directories visited yesterday |
| `j frontend yesterday` | Rank projects visited yesterday by description |
| `j --local api` | Use only local matching |
| `j --list auth backend` | Show matches without changing directories |
| `j --json auth backend` | Show scores, model, elapsed time, and token usage |
| `j --dry-run auth backend` | Inspect the semantic request without sending it |
| `j /path/with\ spaces` | Change directly to an existing directory |
| `j -` / `j` | Previous directory / home |
| `jctl add /path/to/project` | Add a single known directory |
| `jctl index ~/projects` | Add a root and up to 500 immediate visible subdirectories |
| `jctl describe "OAuth authentication backend"` | Set a description for the current directory |
| `jctl list` / `jctl doctor` | Inspect the index / configuration |

Normal `cd` calls also record visits while the integration is loaded. Indexing is shallow: it skips hidden directories, `node_modules`, and `vendor`. It does not recursively scan your home. Repeating `jctl index` adds zoxide visits and can affect its rankings.

Descriptions help when a project has an opaque name or little documentation:

```zsh
cd ~/projects/my-project
jctl describe "Cloudflare Workers chat experiment"
cd ~
j cloudflare chat experiment
```

A strong semantic match changes directories. Close or weaker matches show a numbered picker; Enter cancels. No match or an API error leaves the current directory alone. Ordinary shell input and Enter behavior are unchanged.

Date filters support `today`, `yesterday`, and `last week` (the previous seven complete days), using local calendar boundaries. Tracking starts when this integration is loaded. Existing zoxide entries have no imported per-visit timestamps, and indexing a project does not count as visiting it in the date log.

## How ranking works

1. Resolve existing paths and zoxide name matches locally.
2. Apply any visit-date filter in code.
3. Read bounded metadata for up to 500 indexed directories; shortlist up to 64 using keyword overlap and zoxide rank.
4. Send one batched Jev request with a typed `noul` relevance question per candidate.
5. Jump automatically when the top score is at least 0.80 and leads by at least 0.18. Otherwise offer up to five candidates scoring at least 0.35, or report no match.

These thresholds are initial policy choices, not calibrated accuracy guarantees. A project outside the index or shortlist cannot be selected. Jev returns scores; destinations come exclusively from existing local paths. No generated shell command is evaluated.

The design follows the retrieval, per-candidate scoring, and code-owned decision patterns in [awesome-jev-by-typesafe](https://github.com/Anil-matcha/awesome-jev-by-typesafe#6-semantic-search-and-re-ranking), using the [official TypeSafe API](https://docs.typesafe.ai/) and [zoxide](https://github.com/ajeetdsouza/zoxide).

## Data and configuration

Semantic requests send the query, current directory, candidate paths (home replaced with `~`), project names, descriptions, and technology labels. Descriptions come from your `jctl describe` note, then `package.json`, then a bounded README prose excerpt. Technology labels use filenames and dependency names. Source files, shell history, `.env` files, and package scripts are not included. Project metadata and directory names can still be private; `--dry-run` shows the request before any API call.

Visits and descriptions are appended to private local TSV files under `~/.local/share/joxide` (or `$XDG_DATA_HOME/joxide`). Readers use the last 2 MiB of each log; older visits or descriptions may fall outside that window. Logs are not automatically deleted or compacted. Zoxide keeps its own index.

| Variable | Default / purpose |
| --- | --- |
| `TYPESAFE_API_KEY` | Required only for semantic queries |
| `JOXIDE_MODEL` | `jev-latest` |
| `JOXIDE_NODE` | `node` executable |
| `JOXIDE_ZOXIDE` | `zoxide` executable |
| `JOXIDE_DATA_DIR` | Override the visit/description data directory |
| `_ZO_DATA_DIR` | Zoxide's own index location |
| `_ZO_EXCLUDE_DIRS` | Colon-separated zsh patterns excluded from automatic visit tracking; home is excluded by default |

Set configuration before sourcing. Export variables used by the CLI, such as `JOXIDE_MODEL` and `_ZO_DATA_DIR`. Excluding a directory from tracking does not remove an existing index entry or visit record. If zoxide already has its standard shell hook, this integration avoids adding a second zoxide visit.

## Dependencies and checks

The only direct npm runtime dependency is the pinned official `@typesafe-ai/sdk`. TypeScript and Node types are development dependencies. Installation scripts are disabled in `.npmrc`. Zoxide is a separate native executable.

```zsh
cd "$HOME/.joxide" # Or your checkout directory
npm ci --ignore-scripts # Include development dependencies; tests also need Python 3.9+
npm run check  # Type checking, unit tests, actual zsh/zoxide/Node integration
npm run vet    # /opt/homebrew/bin/vet; npm lockfile and installed zoxide package
```

The integration tests use isolated indexes and a deterministic mock API response through the real SDK. They verify navigation and failure handling, but do not establish live Jev ranking accuracy. Vet reports go into `reports/`; missing provenance or malware coverage is not evidence of safety.
