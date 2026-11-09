# CV / Job Fit Scorer

Upload a CV, paste a job posting, get a fit score — with the full reasoning behind it visible, not just a number.

## How Jev is used

[Jev](https://docs.typesafe.ai) doesn't generate text. It takes a block of `state` text and a set of named `questions`, and returns one **typed** answer per question — a score, a choice, or a yes/no — each with a probability/confidence attached. This app never asks Jev to write anything; it only asks it to judge.

For each submission, the backend builds one `state` string (CV + preferences + job posting) and sends it to Jev's `/v1/systemone` endpoint with:

- **`score`** questions, graded against an ordered rubric — e.g. `fit_score` (poor → excellent)
- **`choice`** questions, one of several named options — e.g. `seniority_match` (too_junior / good_fit / too_senior)
- **`noul`** questions, yes/no as a probability — e.g. `remote_friendly`, `visa_sponsorship_mentioned`

On top of these fixed questions, the app heuristically extracts each individual requirement bullet from the pasted posting (`job_fit_scorer/requirement_extraction.py`) and asks Jev a separate `noul` question per requirement — *"does the candidate profile satisfy this specific requirement?"* The headline fit score is the average of those per-requirement answers (falling back to the holistic `fit_score` question only when no requirements could be extracted), so every point of the score traces back to one specific Jev question and its raw answer — all shown on the result page.

## Project structure

```
job_fit_scorer/   Flask API — Jev integration, requirement extraction, input validation, Swagger docs
frontend/         Next.js + shadcn/ui — upload form, score breakdown, full decision trace
```

## Run it

Backend:

```
cd job_fit_scorer
pip install -r requirements.txt
cp .env.example .env   # add your TYPESAFE_API_KEY
python app.py           # http://localhost:5000  (API docs at /apidocs/)
```

Frontend:

```
cd frontend
npm install
npm run dev              # http://localhost:3000
```

Nothing is persisted — CVs and job postings aren't stored on disk or in a database.
