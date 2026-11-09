# typesafe-ai-jev-demo

A collection of small apps for trying out [Typesafe.ai](https://typesafe.ai) features.

## Apps

| App | What it does | Docs |
| --- | --- | --- |
| [play-4096](./play-4096/) | Plays [4096](https://thereal4096.github.io) (a 2048 variant) via Playwright, asking the SystemOne judgment API (`jev-latest`) for the best move (`up` / `down` / `left` / `right`) until game over | [play-4096/README.md](./play-4096/README.md) |

## Quick start

Each app is self-contained — see its own README for setup and usage. For example:

```bash
cd play-4096
cp .env.template .env   # then put your TYPESAFE_API_KEY into .env
./run.sh
```
