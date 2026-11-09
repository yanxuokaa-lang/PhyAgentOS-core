# TypeSafe (Jev)

Jev is TypeSafe's System One judge: state in, typed noul / choice / score out.
This plugin adds Automations + Pipelines tiles, premade workflows (including
ducky-cluster routing), and `typesafe_*` MCP tools. It is **not** a chat model.

Desktop plugin for [UEFN-Ducky](https://github.com/UEFN-Ducky/UEFN-Ducky) (`typesafe`).
Install or update from **Settings → Store** — do not install from a zip by hand.

## Build

```bash
py scripts/build_zip.py
```

## Secrets

Never commit tokens. The app stores `typesafe_api_key` locally (DPAPI).
Get a key at https://console.typesafe.ai (early access).

## License

MIT. Copyright (c) 2026 Mindful Path Company, LLC. See [LICENSE](LICENSE).
