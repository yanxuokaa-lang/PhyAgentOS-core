# Jev Trader

Local CLI and web desk. **Robinhood Agentic MCP** is the tape and broker. **TypeSafe Jev** votes. **Code** buys once and sells the whole position.

Not financial advice. Default mode is `simulate` ($100 paper book, live quotes). Live orders need yaml `mode: armed` **and** `jev arm`.

## CLI

```bash
npm install
cp .env.example .env   # TYPESAFE_AI_API_KEY
npx tsx src/cli.ts tools
npx tsx src/cli.ts key            # or paste TYPESAFE_AI_API_KEY in the desk
npx tsx src/cli.ts status
npx tsx src/cli.ts watch AAPL --reset --force
```

## Web desk (same brain)

```bash
npm install
npm --prefix web install --legacy-peer-deps
npm run desk
```

- API: `http://127.0.0.1:4177`
- UI: `http://127.0.0.1:5173`

In the UI you can paste the TypeSafe key, click **[WARN] RH LOGIN** for OAuth (`localhost:8787/callback`), and run `[ START ]` / `[ ONCE ]` / `[ STOP ]` / `[ ARM ]` / `[ KILL ]` — same FSM as the CLI.

Design brief: [web/DESIGN.md](web/DESIGN.md). Spec: [docs/JEV.md](docs/JEV.md).

## Tests

```bash
npm test
```
