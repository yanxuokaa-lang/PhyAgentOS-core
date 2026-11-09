# jev-downloads-sorter

A `~/Downloads` folder that sorts itself. Every file that lands there gets one
call to [Jev](https://openrouter.ai/typesafe/jev-1.13), TypeSafe's decision
model, which picks a folder among the ones you defined. About 400 ms per
decision, no prompt to parse, just a choice and a probability.

```
2026-09-19 00:12:52 Facture-Free-septembre-2026.pdf -> Documents/ (jev 1.00 526 ms)
2026-09-19 00:12:54 beat-trap-140bpm.wav -> Audio/ (jev 1.00 380 ms)
2026-09-19 00:12:57 drum_kit_vol3 -> Audio/ (jev 0.99 352 ms)
2026-09-19 00:12:59 notes-reunion.txt -> Documents/ (jev 1.00 473 ms)
```

The extracted drum kit went to Audio, not to Folders. An extension map cannot do that.

## How it works

- A launchd agent with `WatchPaths` on `~/Downloads` runs the script on every change. No daemon, no polling.
- The script takes what sits at the root, skips in-progress downloads (`.crdownload`, `.part`, `.download`), waits 2 s of stable size, then asks Jev.
- Jev sees the name, type, size, the URL the browser recorded on the file (`kMDItemWhereFroms`), the first lines for text files, and the file list for folders.
- If OpenRouter is unreachable it falls back to an extension map. It never creates folders and never overwrites (`name (2).ext`).
- One macOS notification per batch. Log in `~/Library/Logs/jev-downloads-sorter.log`.

Around 200 lines of Python, standard library only.

## Install

Requires macOS and an [OpenRouter](https://openrouter.ai) key. Python 3.12+ via
[uv](https://docs.astral.sh/uv/) or a plain `python3`.

```bash
git clone https://github.com/jolehuit/jev-downloads-sorter
cd jev-downloads-sorter
mkdir -p ~/.config/jev-downloads-sorter
echo 'OPENROUTER_API_KEY=sk-or-...' > ~/.config/jev-downloads-sorter/env
chmod 600 ~/.config/jev-downloads-sorter/env
./install.sh
```

The installer creates the default folders in `~/Downloads`, writes the launchd
plist pointing at this checkout and loads it. macOS will ask once whether
python may access your Downloads folder.

The key is also picked up from `OPENROUTER_API_KEY` in the environment,
`~/.config/zsh/secrets.zsh`, `~/.zshenv` or `~/.env`. launchd does not source
your shell rc, hence the file.

## Your own folders

Write `~/.config/jev-downloads-sorter/folders.json` before running
`install.sh`, a `{"Folder": "what goes there"}` object. The descriptions are
what Jev reads, so say what you mean. Rename or add folders whenever you like,
just keep the file and the folders on disk in sync.

## Uninstall

```bash
./install.sh --uninstall
```

Files stay where they are.

## Why Jev and not a chat model

Sorting a download is a choice among a fixed list. Jev answers exactly that:
`{"choice": "Audio", "confidence": 0.99, "probabilities": {...}}`, in a few
hundred milliseconds, with no free text to parse and no way to invent a folder
that does not exist. The same request works against TypeSafe's own endpoint
(`JEV_SORT_ENDPOINT`).

## Environment

| Variable | Default |
|---|---|
| `JEV_SORT_DIR` | `~/Downloads` |
| `JEV_SORT_CONFIG` | `~/.config/jev-downloads-sorter/folders.json` |
| `JEV_SORT_MODEL` | `typesafe/jev-1.13` |
| `JEV_SORT_ENDPOINT` | `https://openrouter.ai/api/alpha/decisions` |
| `JEV_SORT_STABLE_SECONDS` | `2` |

MIT.
