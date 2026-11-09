# AI-Powered Personal Finance Tracker with Jev

A personal finance tracker powered by TypeSafe AI's Jev model via the official TypeSafe Python SDK (`typesafe-sdk`) or OpenRouter's Decisions API. Instead of slow, conversational text generation, the application uses structured, typed decisions (`choice`, `noul`, `score`) with calibrated probabilities evaluated in parallel.

## Architecture

The system cleanly splits semantic AI decisions from deterministic application logic:

- **TypeSafe Jev Decisions Engine**:
  - `choice` primitive: Selects the most accurate category out of predefined criteria with calibrated confidence.
  - `noul` primitive (subscription): Evaluates if a transaction is a recurring subscription (`0.0` to `1.0` probability).
  - `noul` primitive (duplicate): Analyzes recent transactions to flag accidental duplicate swipes.
  - `score` primitive (anomaly): Rates transaction deviation on an ordered 1-to-5 rubric.
- **Configurable Provider Architecture**:
  - `jev` (default): Uses the official TypeSafe AI SDK (`typesafe-sdk`) with direct calls to `https://api.typesafe.ai` and `jev-latest`. Configured with `JEV_API_KEY`.
  - `openrouter`: Uses OpenRouter's Decisions API (`/api/alpha/decisions`) with `typesafe/jev-1.13`. Configured with `OPENROUTER_API_KEY`.
  - Configurable via `JEV_PROVIDER=jev` or `JEV_PROVIDER=openrouter` in `.env`.
- **Deterministic Application Engine**:
  - Budget calculations (`spent + amount > category_limit`) are executed deterministically in Python rather than estimated by an LLM.
  - Calibrated threshold gating: Decisions with category confidence below 0.80 are flagged for human review; subscriptions are registered when probability is 0.70 or higher; duplicates are flagged when probability is 0.80 or higher.
- **Strict Fail-Fast Policy**:
  - Direct integration without mock fallbacks. If the selected provider API key is not set or the upstream API returns an error, the backend raises an explicit HTTP 502 response.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic v2, `typesafe-sdk`, `uv`, `black`, `pytest`.
- **Frontend**: React 18, TypeScript (`strict: true`), Vite, Tailwind CSS, Lucide icons, `pnpm`.

## Setup and Running

### 1. Environment Configuration

Copy the example configuration file at the repository root and provide your API key:

```bash
cp .env.example .env
```

Configure `JEV_PROVIDER` (defaults to `jev`) and supply the corresponding key:

- When `JEV_PROVIDER=jev`: set `JEV_API_KEY`
- When `JEV_PROVIDER=openrouter`: set `OPENROUTER_API_KEY`

### 2. Quickstart with Makefile

Run common tasks directly from the repository root:

```bash
# Setup both backend and frontend dependencies
make setup

# Start both services in background
make start

# Check service status
make status

# Run test suites
make test

# Format code with black
make format

# Stop all background services
make stop
```

### 3. Manual Backend Setup

From the `backend/` directory:

```bash
uv venv
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload --port 8000
```

To run the backend test suite:

```bash
uv run pytest
```

### 4. Frontend Setup

From the `frontend/` directory:

```bash
pnpm install
pnpm dev
```

The frontend will be available at `http://localhost:5173`. It automatically proxies API requests to `http://localhost:8000`.

## API Endpoints

- `POST /api/transactions`: Submits transaction details, runs Jev decisions, checks budget math, and persists.
- `GET /api/transactions`: Lists transactions with filters (`needs_review`, `is_anomaly`, `category`).
- `PATCH /api/transactions/{id}`: Approves or reassigns categories for flagged transactions.
- `DELETE /api/transactions/{id}`: Deletes a transaction.
- `GET /api/budgets`: Returns current month spend, remaining balance, and utilization per category.
- `PUT /api/budgets`: Updates category monthly limits.
- `GET /api/subscriptions`: Returns detected recurring subscriptions.
- `PATCH /api/subscriptions/{id}`: Toggles active status.
- `GET /api/stats`: Month-to-date aggregates, active warnings, and breakdown.
- `GET /health`: Health check endpoint.
