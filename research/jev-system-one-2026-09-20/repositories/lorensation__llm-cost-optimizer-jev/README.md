# LLM Cost Autopilot

An evidence-based LLM router that chooses the lowest expected-cost qualified route, verifies every output before release, and records complete cost provenance. The repository starts safely in fixture mode: it makes no paid calls and makes no savings claim.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev,dashboard]"
.venv\Scripts\pytest -q
.venv\Scripts\python scripts/smoke_providers.py
.venv\Scripts\uvicorn app.api:app --reload
```

Try the fixture API:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/generate `
  -H "Content-Type: application/json" -H "Idempotency-Key: demo-1" `
  -d '{"contract_id":"extract_invoice_v1","request":"Extract the invoice","source":"Invoice F-104. Total: 120 EUR."}'
```

The response includes the immutable policy snapshot, model, checks, attempt count, and cost status. `contract_passed` means all configured gates passed; it is not a claim of guaranteed factual truth.

## Safety and real mode

Copy `.env.example` and configure credentials only server-side. A real smoke is opt-in and refuses to start without both credentials and an explicit budget:

```powershell
python scripts/smoke_providers.py --real --max-budget-microusd 10000
```

Do not set `mode: active` with fixture profiles. Real routing requires measured profiles, calibrated checks, representative labels, and a promotion decision. See [progress](docs/progress.md), [decisions](docs/decisions.md), and [provider contracts](docs/provider-contracts.md).

## Services

- API: `uvicorn app.api:app`
- Audit worker: `python -m app.worker`
- Dashboard: `streamlit run dashboard/app.py`
- Containers: `docker compose up` (add `--profile dashboard` for Streamlit)

SQLite uses WAL, atomic reservations, durable audit leases, and idempotency keys. A network timeout preserves unknown cost instead of silently treating it as zero. The system permits at most two generation attempts and verifies the final attempt as well.

## Experimental status

Phases requiring real providers or human labels are deliberately not represented as complete. The synthetic profiles and fixture outputs test behavior only. `PLAN-Final.md` is the specification and `STEPS.md` is the execution ledger.
