# Jev · MECE Use-Case Map

Inspired, mobile-first showcase of TypeSafe **Jev** use cases from the first days on X — organized as a MECE taxonomy. Switchboard hero + sticky rail; all six pillars always expanded as a reference map.

**Live:** https://galigutta.github.io/jev-use-cases/

## Structure

Six mutually exclusive pillars (short names match the switchboard):

1. Workflow  
2. Bulk  
3. Realtime  
4. Verify  
5. Harness  
6. Voice (turn-taking, speak-up, voice→action)  

Independent community compilation — **not affiliated with TypeSafe AI**.

## Propose a use case

Anyone can suggest a new leaf. Static GitHub Pages **cannot** hold API keys — grading and PR drafting run in GitHub Actions.

### Flow

1. **Site** — Use **Propose a use case** on the live map. A Cloudflare Worker grades with **Jev in-request**. Duplicates get an on-page verdict only (no GitHub issue). Novel proposals `repository_dispatch` into Actions with the Worker verdict (no second Jev call) → Codex leaf → auto-merge. Manual [issue form](https://github.com/galigutta/jev-use-cases/issues/new?template=propose_use_case.yml) still works as a fallback path.
2. **Jev grades** — Workflow `.github/workflows/propose-use-case.yml` extracts the current leaves from `docs/index.html`, then calls TypeSafe Jev (`POST https://api.typesafe.ai/v1/systemone`) in a **two-stage packed** call (pillar route → novelty vs peers) so state stays under Jev’s context limits. The novelty bar is **high and saturates** with catalog size (overlap-first (none → add); gray-zone noul ≥ ~0.58→0.78 and score ≥ ~2.4→3.3 as leaves approach 200); confident overlap forces duplicate.
3. **If duplicate** — The Action comments the saturated-threshold verdict on the issue and stops.
4. **If novel** — Codex (`openai/codex-action`, model `gpt-5.6-luna`, effort `max`) edits `docs/index.html` to add one leaf under the chosen pillar, opens a PR, **auto-merges** it to `main` (squash + delete branch), and comments / closes the issue.

```
You → GitHub issue [propose]
        ↓
   extract_use_cases.py
        ↓
   grade_novelty.py  (TYPESAFE_API_KEY → Jev, two-stage + sat bar)
        ↓
   novel? ──no──► comment + stop
        │ yes
        ↓
   build_codex_prompt.py
        ↓
   openai/codex-action  (OPENAI_API_KEY · gpt-5.6-luna · effort max)
        ↓
   commit · push · gh pr create · auto-merge · comment/close
```

### Required repository secrets

Set these under **Settings → Secrets and variables → Actions** (never in `docs/`):

| Secret | Used by | Purpose |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | `scripts/grade_novelty.py` | TypeSafe Jev System One API |
| `OPENAI_API_KEY` | `openai/codex-action@v1` | Codex leaf authoring |

`GITHUB_TOKEN` (automatic) is enough to push a branch, open a PR, and auto-merge on this public repo (no branch protection).

### Manual / dispatch triggers

- **Issue** opened or labeled with `propose`, or title starting with `[propose]`
- **workflow_dispatch** inputs: `proposal`, optional `source_url`
- **repository_dispatch** type `propose_use_case` with `client_payload.proposal` / `.source_url`

## Scripts

```bash
python3 scripts/extract_use_cases.py --out use_cases.json
TYPESAFE_API_KEY=… python3 scripts/grade_novelty.py \
  --proposal "…" --source-url "…" --inventory use_cases.json --out novelty.json
python3 scripts/build_codex_prompt.py --novelty novelty.json --out codex-prompt.md
```

## Local

Open `docs/index.html` in a browser, or:

```bash
npx serve docs
```

## Pages

GitHub Pages serves from `/docs` on `main`.
