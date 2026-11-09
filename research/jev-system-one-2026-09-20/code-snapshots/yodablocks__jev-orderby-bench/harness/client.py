"""Jev client: batching, on-disk cache, and token metering.

This is Phase 1 infrastructure that Phase 3 reuses rather than replaces.
Three of the Phase 3 execution-layer requirements are cheaper to build now
than to retrofit:

- Batching. Jev answers many questions against one state in a single
  parallel pass, so per-row-per-question calls waste the architecture.
  `ask` sends every question for a row in one request.
- Cache. Keyed on a content hash of (model, state, questions). Re-running
  the notebook must be free, otherwise nobody re-runs it.
- Cost metering. Rate limits and per-token pricing are undocumented, so
  the Phase 3 cost ceiling can only be calibrated from usage we measure
  ourselves. Every response records input/output tokens from call one.

API contract verified against docs.typesafe.ai on 2026-09-18:
  POST https://api.typesafe.ai/v1/systemone
  Authorization: Bearer <key>
  {"state": ..., "model": "jev-latest", "questions": {id: {...}}}
  -> {"model", "answers": {id: {...}}, "usage": {input_tokens, output_tokens}}
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"

# The build spec names TYPESAFE_AI_API_KEY; the published Python SDK page
# names TYPESAFE_API_KEY. Accept either rather than guessing.
KEY_VARS = ("TYPESAFE_AI_API_KEY", "TYPESAFE_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    """Locate the enclosing git repository root.

    Do NOT hardcode a parent depth. This project started as a
    subdirectory of a larger repo and graduated into its own, which
    changed the nesting depth. A hardcoded parents[3] silently resolved `.data/`
    to the user's HOME directory after that move: outside the repo, so
    the cache and corpus landed somewhere the .gitignore did not cover.
    """
    d = PROJECT_ROOT
    for candidate in (d, *d.parents):
        if (candidate / ".git").exists():
            return candidate
    return d


# Where to look for a .env file: the project root, then the repo root if
# it differs (they are the same once this is a standalone repo).
_ENV_SEARCH = tuple(
    dict.fromkeys((PROJECT_ROOT / ".env", repo_root() / ".env"))
)


def load_env(verbose: bool = False) -> str | None:
    """Load a .env file if present, without clobbering a real env var.

    An already-exported variable always wins: if you have a key in your
    shell, a stale .env should not silently override it.

    Uses python-dotenv when installed and falls back to a small parser
    otherwise, so the harness never hard-depends on it.
    """
    for path in _ENV_SEARCH:
        if not path.is_file():
            continue
        try:
            from dotenv import load_dotenv

            load_dotenv(path, override=False)
        except ImportError:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().removeprefix("export ").strip()
                v = v.strip().strip("'\"")
                os.environ.setdefault(k, v)
        if verbose:
            print(f"loaded env from {path}")
        return str(path)
    return None


class BudgetExceeded(RuntimeError):
    """Raised when the token ceiling is hit. Fails loud, by design."""


class NoAPIKey(RuntimeError):
    pass


def api_key() -> str:
    if not any(os.environ.get(v) for v in KEY_VARS):
        load_env()
    for var in KEY_VARS:
        if os.environ.get(var):
            return os.environ[var]
    raise NoAPIKey(
        "No API key found.\n\n"
        f"Either create {_ENV_SEARCH[0]} containing:\n"
        "    TYPESAFE_AI_API_KEY=your-key-here\n\n"
        "or export it in your shell:\n"
        "    export TYPESAFE_AI_API_KEY=your-key-here\n\n"
        f"Accepted variable names: {', '.join(KEY_VARS)}"
    )


def has_api_key() -> bool:
    if any(os.environ.get(v) for v in KEY_VARS):
        return True
    load_env()
    return any(os.environ.get(v) for v in KEY_VARS)


# --- question builders -------------------------------------------------
# Thin wrappers so the notebook never hand-writes request JSON and the
# shapes stay in one place.

def noul(instructions: str, criteria: dict | None = None) -> dict:
    q: dict[str, Any] = {"type": "noul", "instructions": instructions}
    if criteria:
        q["criteria"] = criteria
    return q


def choice(instructions: str, criteria: dict) -> dict:
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions: str, criteria: list) -> dict:
    return {"type": "score", "instructions": instructions, "criteria": criteria}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    cache_hits: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Cache:
    """Content-addressed response cache.

    SQLite over parquet: concurrent writers from the bounded pool need row
    level durability, and re-running one row should not rewrite a file.
    """

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._local = threading.local()
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS responses (
                       key TEXT PRIMARY KEY,
                       model TEXT NOT NULL,
                       request TEXT NOT NULL,
                       response TEXT NOT NULL,
                       input_tokens INTEGER,
                       output_tokens INTEGER,
                       latency_ms REAL,
                       created_at REAL
                   )"""
            )

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.path, timeout=30)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    @staticmethod
    def key(model: str, state: Any, questions: dict) -> str:
        blob = json.dumps(
            {"model": model, "state": state, "questions": questions},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(blob.encode()).hexdigest()

    def get(self, key: str) -> dict | None:
        row = self._conn().execute(
            "SELECT response FROM responses WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key, model, request, response, latency_ms) -> None:
        usage = response.get("usage", {})
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO responses VALUES (?,?,?,?,?,?,?,?)",
                (
                    key,
                    model,
                    json.dumps(request, ensure_ascii=False),
                    json.dumps(response, ensure_ascii=False),
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    latency_ms,
                    time.time(),
                ),
            )

    def stats(self) -> dict:
        r = self._conn().execute(
            "SELECT COUNT(*), COALESCE(SUM(input_tokens),0), "
            "COALESCE(SUM(output_tokens),0), AVG(latency_ms) FROM responses"
        ).fetchone()
        return {
            "cached_responses": r[0],
            "input_tokens": r[1],
            "output_tokens": r[2],
            "mean_latency_ms": r[3],
        }


class JevClient:
    """Cached, budgeted, retrying client.

    token_budget is a hard ceiling that raises rather than degrading. An
    ORDER BY over a large table is an easy way to spend real money by
    accident, so the failure mode is a loud stop, not a silent partial run.
    """

    def __init__(
        self,
        cache_path: Path,
        model: str = DEFAULT_MODEL,
        token_budget: int | None = None,
        max_retries: int = 5,
        timeout: float = 90.0,
    ):
        self.cache = Cache(cache_path)
        self.model = model
        self.token_budget = token_budget
        self.max_retries = max_retries
        self.timeout = timeout
        self.usage = Usage()
        self._lock = threading.Lock()
        self._session = requests.Session()

    def ask(self, state: Any, questions: dict, use_cache: bool = True) -> dict:
        """Send every question for one state in a single request."""
        key = Cache.key(self.model, state, questions)

        if use_cache:
            hit = self.cache.get(key)
            if hit is not None:
                with self._lock:
                    self.usage.cache_hits += 1
                return hit

        body = {"state": state, "model": self.model, "questions": questions}
        response = self._post(body)

        usage = response.get("usage", {})
        with self._lock:
            self.usage.input_tokens += usage.get("input_tokens", 0)
            self.usage.output_tokens += usage.get("output_tokens", 0)
            self.usage.requests += 1
            if (
                self.token_budget is not None
                and self.usage.total_tokens > self.token_budget
            ):
                raise BudgetExceeded(
                    f"Token budget exceeded: {self.usage.total_tokens} "
                    f"> {self.token_budget}. Raise token_budget or narrow the query."
                )
        return response

    def _post(self, body: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
        }
        last = None
        for attempt in range(self.max_retries):
            started = time.time()
            try:
                r = self._session.post(
                    ENDPOINT, headers=headers, json=body, timeout=self.timeout
                )
            except requests.RequestException as exc:
                last = exc
                self._backoff(attempt)
                continue

            latency_ms = (time.time() - started) * 1000

            if r.status_code == 200:
                payload = r.json()
                key = Cache.key(self.model, body["state"], body["questions"])
                self.cache.put(key, self.model, body, payload, latency_ms)
                return payload

            # 429 rate limit and 529 overloaded are the documented retryables.
            if r.status_code in (429, 529) or r.status_code >= 500:
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
                self._backoff(attempt, r.headers.get("retry-after"))
                continue

            # 401 auth and 422 validation will not improve on retry.
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")

        raise RuntimeError(f"Failed after {self.max_retries} attempts: {last}")

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                time.sleep(min(float(retry_after), 60))
                return
            except ValueError:
                pass
        time.sleep(min(2**attempt, 30) * (0.5 + random.random()))
