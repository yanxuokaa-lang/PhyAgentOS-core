# JEV Resume Analyzer

Review a CV with fast, structured AI judgments, optionally against a job posting. Upload a PDF or DOCX, check the extracted text, and get a traceable report: every assessment shows the exact question, criteria, answer, and probability distribution behind it.

Built on [TypeSafe](https://typesafe.ai) (System One model, `jev-latest`): structured judgments composed in code, not prompt-and-parse text generation.

## What it does

- **Full-document CV review**: work clarity, personal contribution, interpretability, outputs/results, scope, and optional-summary specificity, each as a typed judgment over the whole document.
- **Optional job alignment**: paste a posting; two document-level questions assess how the CV evidences relevant responsibilities and qualifications.
- **Honest uncertainty**: four answer outcomes (`present`, `absent`, `not_applicable`, `unable_to_assess`) with real probability distributions. "No summary" is not a defect; "unable to assess" is not a zero.
- **Traceable findings**: expand any finding to see the evaluated question, its criteria, the answer, and per-option probabilities. Explanations are predefined rubric text, clearly labelled: never generated advice.
- **Privacy-first demo**: no accounts, no database, no localStorage for CV text, no client-side keys. One Jev request per analysis; failed requests never produce fabricated reports.

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | React 18, Vite, TypeScript, Zod-validated API contract |
| Backend | FastAPI, Pydantic, pypdf, defusedxml (DOCX XML traversal) |
| AI | TypeSafe System One API (`jev-latest`), one batched request per analysis |

## Quick start

Requirements: Python 3.11+, Node 20.19+ or 22.12+, [uv](https://docs.astral.sh/uv/), a TypeSafe API key.

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env and set TYPESAFE_API_KEY
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8017

# Frontend (second terminal)
cd frontend
npm ci
npm run dev
# open http://127.0.0.1:5273
```

The Vite dev server proxies `/api` to the backend on `127.0.0.1:8017`.

## Tests

```bash
# Backend: 69 synthetic tests + lint (live test is gated behind JEV_RUN_LIVE=1 and a running API)
cd backend && uv run pytest -q && uv run ruff check app tests

# Frontend: 30 tests, typecheck, build
cd frontend && npm test && npm run typecheck && npm run build

# Browser flows (needs Chromium; see docs/frontend-contract.md)
cd frontend && CHROMIUM_PATH=<chromium-binary> npx playwright test
```

## Design boundaries

- Full-document assessments only; no fabricated bullet-level findings.
- No overall rating is shown yet: scoring maps stay `null` until calibrated on reviewed examples.
- No hiring predictions, ATS scores, truthfulness verdicts, or generated rewrites.
- Localhost demo: CV text is sent to TypeSafe for analysis; retention terms should be verified before any public deployment.

## Docs

- `docs/architecture.md`: proposed architecture, API contracts, runtime flow
- `docs/frontend-contract.md`: binding frontend↔backend schema (implemented in `frontend/src/api/schema.ts`)
- `docs/backend-implementation.md`: backend verification evidence and contract decisions
- `docs/frontend-contract.md` and the rubric modules under `backend/app/rubrics/` define what every question means

## Status

Working end-to-end on localhost: upload → editable extraction preview → one batched Jev request → traceable report. Deferred: generated suggestions (phase 2), OCR, accounts, public deployment.
