# Jev prototypes

Practice lab for [TypeSafe Jev](https://docs.typesafe.ai/) apps. Not a product.

The host is a gallery: it auto-discovers `prototypes/*/proto.yaml` and mounts live apps under `/p/<slug>/`.

## Run locally

```bash
cp .env.example .env   # set TYPESAFE_API_KEY from https://console.typesafe.ai/
uv sync
uv run uvicorn host.app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 — gallery, click a prototype.

## Tests

```bash
uv run pytest
```

## Add a prototype

Copy `prototypes/_template` and follow [prototypes/_template/README.md](prototypes/_template/README.md).

In short: copy the folder to `prototypes/<slug>` (name must match `proto.yaml` `slug` and must not start with `_`), rename the Python package, fill `proto.yaml` (`status: live`), replace the echo stub with Jev questions, add any new pip deps to the **root** `pyproject.toml` and `uv lock`, use relative `api/...` URLs. The host picks up `prototypes/*/proto.yaml`. No host code change.

## Deploy on Fly.io

`Dockerfile` and `fly.toml` are in the repo (app name `jev-lab`, region `sjc`, 512mb shared CPU, autostop). Live URL: https://jev-lab.fly.dev/

From the repo root:

```bash
fly deploy --ha=false -a jev-lab
fly secrets set TYPESAFE_API_KEY=... -a jev-lab   # only if rotating
```

The public URL needs no login. POSTs under `/p/` are rate-limited (10/min/IP) so random traffic cannot empty the key as easily. The first request after idle may cold-start.
