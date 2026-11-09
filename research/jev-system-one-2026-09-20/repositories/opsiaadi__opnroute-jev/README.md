# jev-mcp

MCP server for JEV (TypeSafe System One) classification via OpenRouter. Exposes structured decision tools (noul, choice, score) for Hermes and other MCP clients.

## What it does

Classifies text using JEV via OpenRouter's Streamable HTTP API. Tools:

- **classify** — classify text into noul (yes/no), choice (multi-class), and score (sentiment/priority) decisions
- **classify_batch** — classify multiple texts in one call
- **health** — check if the classifier is ready

## Requirements

- Python 3.10+
- OpenRouter API key (https://openrouter.ai/keys)
- `mcp` Python package (included in Hermes venv, or install: `pip install mcp[cli]`)

## Quick install (Hermes)

### HTTP/SSE (recommended — works across all devices)

```bash
# 1. Clone repo
git clone https://github.com/opsiaadi/jev-mcp.git
cd jev-mcp

# 2. Set API key (only once)
echo "OPENROUTER_API_KEY=sk-or-xxx" >> ~/.hermes/.env

# 3. Start server (bind 0.0.0.0 for multi-device access)
python3 jev_classifier_http.py 0.0.0.0 8765

# 4. Register in Hermes (from any device that can reach the server)
hermes mcp add jev-http --url http://<server-ip>:8765/mcp
```

Hermes will prompt for API key on first connection.

### Stdio (single device only)

```bash
hermes mcp add jev-classifier --command python3 --args /path/to/jev_classifier.py --env OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY
```

## Install (non-Hermes clients)

### Claude Desktop

In `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "jev-http": {
      "url": "http://<server-ip>:8765/mcp"
    }
  }
}
```

### Cursor

In Cursor settings → MCP → add server with URL `http://<server-ip>:8765/mcp`.

### Any MCP client

Connect to the Streamable HTTP endpoint: `http://<server-ip>:8765/mcp`. No auth header needed (API key loaded server-side from `.env`).

## Optional: protect the server with a token

For public / multi-device deployments, start the server with `MCP_AUTH_TOKEN` set. The server then requires every request to `/mcp` to carry `Authorization: Bearer <MCP_AUTH_TOKEN>` and returns `401` otherwise. Leave it unset to keep the server open (LAN-only).

```bash
# On server
export MCP_AUTH_TOKEN="***"
python3 jev_classifier_http.py 0.0.0.0 8765

# On any other device — pass the token as a header
hermes mcp add jev-http --url http://<server-ip>:8765/mcp --auth header
# then set header: Authorization: Bearer <MCP_AUTH_TOKEN>
```

For clients that only take a plain URL, a reverse proxy or firewall rule is the safer choice than an open `0.0.0.0` bind.

## Multi-device access

When running on a server (VPS, home server), bind to `0.0.0.0` so other devices on your network (or with proper port forwarding) can connect:

```bash
# On server
python3 jev_classifier_http.py 0.0.0.0 8765

# On any other device
hermes mcp add jev-http --url http://<server-ip>:8765/mcp
```

## Files

- `jev_classifier.py` — stdio MCP server (no server process needed)
- `jev_classifier_http.py` — Streamable HTTP MCP server (needs uvicorn + mcp 2.0+)

## Development

```bash
# Install deps (if not in Hermes venv)
uv pip install mcp uvicorn starlette

# Run HTTP server
python3 jev_classifier_http.py 127.0.0.1 8765

# Or with custom model/endpoint env vars
JEV_MODEL=typesafe/jev-1.13 OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY python3 jev_classifier_http.py
```

## Security notes

- API key is loaded from `~/.hermes/.env` or `OPENROUTER_API_KEY` env var. Never commit it.
- Default bind is `127.0.0.1`. Use `0.0.0.0` only on trusted networks.
- For public deployment, add authentication (reverse proxy, VPN, or `transport_security` in SDK).

## License

MIT
