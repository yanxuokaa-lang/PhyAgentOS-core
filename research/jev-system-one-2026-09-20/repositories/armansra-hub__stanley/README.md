# Stanley

Stanley is a single-user prospecting and workflow assistant for a NetSuite account executive. It combines a hosted application with local, supervised sales workflows. The package name remains `jarvis`; the product is Stanley.

**Next.js · Supabase · Jev (TypeSafe) · Claude · Vercel**. Jev interprets source evidence and guides account research; Claude provides chat, account-story writing, and the separate legacy classification path. See the [Jev usage and code map](docs/JEV_USAGE.md).

**Sharing this with a colleague?** Start with the [architecture and logic guide](docs/ARCHITECTURE.md), then [setup and infrastructure](docs/SETUP.md) and the [local workflow guide](operations/README.md).

**Explore the broader work library:** [Codex Automations](codex-automations/README.md) catalogs the systems, skills, dashboards, research tools, deal-memory workflows, and historical experiments found across 12 local Codex projects. Reviewed September 11, 2026, with explicit status, evidence, infrastructure, schedules, and coverage limits.

This documentation was reconciled with GitHub `main` and the local Stanley workspace on **2026-09-09**. See the [reconciliation report](docs/SOURCE_RECONCILIATION.md) for scope and provenance. Repository configuration describes intended behavior; live database counts, configured models, scheduler status, and deployment state require authenticated readback.

## What Stanley does

| Surface | Purpose | Main implementation |
|---|---|---|
| Headhunter (`/headhunter`) | Import and monitor the TAM, manage the claimed TAL, review public signals, and prioritize TAM / Old Gold worklists | `components/Dashboard.tsx`, `lib/db/companies.ts`, `app/api/headhunter/` |
| Account Intelligence | Jev source interpretation, operating-topic matches, saved research questions, and directed research; cited account stories use Claude | `lib/intelligence/`, [Jev usage map](docs/JEV_USAGE.md) |
| Missions (`/missions`) | Tasks, reminders, recurring work, time placement around Outlook busy blocks, and conversational actions | `lib/missions/`, `lib/db/missions.ts` |
| Kill List (`/kill-list`) | Manually maintained pipeline, activity history, and dated tasks linked to Missions | `lib/killlist/`, `lib/db/killlist.ts` |
| Ask Stanley | Chat and voice-assisted access to application tools | `lib/chat/`, `app/api/chat/` |
| Local workflows | NetSuite evidence review, Outlook cadence, LinkedIn outreach, event invitations, and verified CRM touch logging | [operations/](operations/README.md) |

The hosted app does not replace the operator's authenticated Chrome session. Outbound prospecting runs locally under workflow rules, exact identity checks, durable state, and external verification.

## Three different kinds of prioritization

- **TAM:** `codex_score` is the raw 0–100 close-probability judgment from the NetSuite record. `tam_score` preserves it except for record-dead and confirmed NetSuite-incumbent hard zeros. Low scores are valid; do not curve them.
- **Old Gold:** historical revival potential with its own evidence-based score. Membership requires qualifying note/prior-SQL evidence or an audited dated opportunity. A non-member has `oldgold_score = null` in live storage; a full assessment can still explicitly record `old_gold_score: 0`.
- **Triggered:** public evidence of growth and operational change, ranked with signal strength, decay, and fit. Public signals never alter TAM or Old Gold grades.

TAL replacement uses exact NetSuite Internal IDs, rejects unresolved or ambiguous membership before writing, commits atomically, and verifies the result. Names and domains are context, not TAL identity keys.

## Runtime and infrastructure

Next.js 15 App Router, React 19, TypeScript, and Tailwind run on Vercel. Supabase Postgres stores business state, trigger evidence, tasks, and audit records; database service credentials remain server-only. Jev runs through the direct TypeSafe API for evidence interpretation and research ranking. Anthropic powers conversational tools, cited account-story writing, and the separate legacy classifier/reviewer. Models are configurable; different components have different code defaults.

The optional [direct Jev intelligence engine](docs/INTELLIGENCE.md) adds changed-source interpretation, saved research questions, operating-pattern matches and cited company profiles. Eligible Jev findings publish directly to Triggered with their source passage and preserved model judgments; no second-model or candidate review is added to that path. Existing legacy collectors keep their review behavior. Short cloud jobs collect and interpret evidence on five- and fifteen-minute schedules once enabled. It calls TypeSafe directly; no Vercel AI Gateway connection is required.

Account Intelligence opens inside the lead record and retains the originating filters, notes and scroll. [Business-services research](docs/BUSINESS_SERVICES_RESEARCH.md) uses the actual territory's subindustries, preserves native Jev packet findings and separates initial account coverage from deeper reading. A dedicated research schedule follows discovered but unread company sources as well as due refreshes. Operating Matches supports Any/All across 21 operating topics with distinct account counts. Local TAM navigation helpers keep private indexes on the operator's computer; the canonical local grader remains paused, and cloud deployment does not resume it.

`vercel.json` invokes `/api/cron/daily` **hourly**, despite its historical name. Each invocation runs one five-request stage from an 80-request manifest, giving a 16-stage rotation. Prime-award checks and candidate review appear in every stage. Data foundation imports are separate jobs. Coverage targets are plans, not guarantees that a provider succeeded.

Federal discovery also runs every five minutes in bounded batches over current TAM companies without a verified federal recipient/award link. A verified identity and first award enroll the company into the existing award sweeps. Provider errors remain visible in the source checkpoint; a scheduled attempt does not mean a successful match or complete history. Two repeated timeouts at the same stage hold that company for the current request strategy, including after the selection cursor wraps; a successful lookup resets an unheld timeout count. The authenticated `/api/cron/federal-discovery?inspect=1` endpoint reads progress and exact holds without starting a sweep or changing its state.

Production source is **GitHub `armansra-hub/stanley`, branch `main`**, through the existing Vercel Git integration. The source guard, platform permissions, and exact post-deploy source readback are the release controls. Do not deploy a local directory or prebuilt upload to production.

## Local development

Use Node.js 20 or later and npm. The committed `package-lock.json` is the dependency lockfile.

```bash
npm ci
cp .env.example .env.local
# Configure your own development Supabase project and credentials.
# Apply the reviewed migration set described in docs/SETUP.md.
npm run dev
```

PowerShell users can use `Copy-Item .env.example .env.local` instead of `cp`.

```bash
npm test
npx tsc --noEmit
npm run check:production-source
```

`npm run build` generates art and builds the application. A complete production release also requires migration and deployed-source verification.

## Repository map

| Directory | Contents |
|---|---|
| `app/`, `components/` | Pages, UI, and server route handlers |
| `lib/` | Domain logic, database access, ingestion, agent tools, and tests |
| `config/` | Territory, sources, signals, and dated baseline receipts |
| `supabase/migrations/` | Ordered SQL schema and transactional guards |
| `scripts/`, `tools/` | Application foundation, evidence registration, and verification utilities |
| `operations/` | Local workflow specification and reviewed source snapshots; not hosted automation |
| `docs/` | Architecture, setup, reconciliation, and signal quarantine runbook |
| `codex-automations/` | Cross-project automation and work-product catalog, schedules, evidence, and coverage |
| `public/art/` | Versioned assets shipped with Git-sourced builds |

This repository is public. Credentials, CRM exports, contact lists, mailbox threads, browser sessions, PDF evidence, live ledgers, and access grants remain outside it. Cloning the code does not grant access to the existing app, database, accounts, or customer records.
