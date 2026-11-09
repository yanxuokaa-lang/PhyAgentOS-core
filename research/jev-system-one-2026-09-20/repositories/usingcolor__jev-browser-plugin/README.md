# Jev Browser (agent plugin)

Cursor / Agent Plugins package that teaches agents to automate websites with **high-level goals** via the Mac `jev-browser` CLI (TypeSafe Jev indexed controls), instead of screenshot computer-use.

## Contents

| Skill | Purpose |
|-------|---------|
| `jev-browser` | When/how to invoke the CLI and parse JSON |
| `jev-browser-setup` | Install the Mac CLI + env |

## What it does **not** include

- API keys
- A hosted browser
- Guaranteed Mac hardware for importers

Importers need a registered Mac with [jev-browser](https://github.com/usingcolor/jev-browser) installed.

## Install (developers)

### Local test (Cursor)

```bash
mkdir -p ~/.cursor/plugins/local/jev-browser
rsync -a --delete \
  --exclude .git \
  ~/Codes/jev-browser-plugin/ \
  ~/.cursor/plugins/local/jev-browser/
# then: Developer: Reload Window
```

### Marketplace

1. Make this repository **public**.
2. Submit the repo URL at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).
3. Cursor reviews manually before listing.

## Related

- CLI: https://github.com/usingcolor/jev-browser

## License

MIT


## Typing without a text LLM

Callers should put form strings in request `fields`. TYPE_TEXT resolves from those values; a text LLM is optional fallback only.

## Marketplace listing fields

- **Logotype URL:** `https://raw.githubusercontent.com/usingcolor/jev-browser-plugin/main/assets/logo.svg`
- **PNG (optional):** `https://raw.githubusercontent.com/usingcolor/jev-browser-plugin/main/assets/logo.png`
- **Description:** High-level GOAL→JSON browser automation via TypeSafe Jev indexed controls. Prefer over screenshot computer-use for multi-step website tasks. Requires a Mac host with the jev-browser CLI.
