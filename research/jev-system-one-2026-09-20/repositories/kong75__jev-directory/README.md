# Jev Directory

Discover Jev projects. Learn from their creators. Reuse a useful example.

A free, independent directory with six projects and demos, nine copyable examples, and five educational guides. Projects explain where Jev fits and credit their original creators. Examples include complete questions, sample inputs, typed answers, application policies, and license-aware code downloads. Original X posts load on demand. No model API calls are made by the website.

**Status:** the redesigned library is deployed at [jev-directory.com](https://jev-directory.com) with automatic GitHub deployments. Source and contribution forms are public at [github.com/kong75/jev-directory](https://github.com/kong75/jev-directory). Optional sponsor contact and analytics remain unconfigured; no live model quality claims are made.

## Development

Requires Node.js 24 and pnpm 10.

```sh
pnpm install --frozen-lockfile
pnpm dev
pnpm check
pnpm test
pnpm build
pnpm test:e2e
```

## Implementation handoff

Read these in order:

0. [Projects and examples](docs/PROJECTS-AND-EXAMPLES.md): current discovery, data model, attribution, and widget contract. [Decision-library contract](docs/DECISION-LIBRARY.md) continues to govern copy/download behavior.

1. [Implementation plan](docs/IMPLEMENTATION-PLAN.md): authoritative product, architecture, behavior, milestones, and acceptance criteria.
2. [Design specification](docs/DESIGN.md): visual system, page composition, and responsive behavior.
3. [Content brief](docs/CONTENT.md): source-backed launch inventory and editorial contract.
4. [Research notes](docs/research-notes.md): earlier browser observations, explicitly not runtime validation.
5. [Agent instructions](AGENTS.md): execution boundaries and working conventions.

### Prompt for a continuing agent

> Continue Jev Directory from docs/BUILD-STATUS.md. Preserve the editorial and evidence rules in the implementation plan. Complete only the external configuration that has been authorized, rerun the validation gates, and update the status document with the exact public URL and checks performed.

## Maintain the directory

The repository includes [Jev Curator](.agents/skills/jev-curator/SKILL.md), a skill for finding and consistently documenting projects, creator demos, and copyable examples. It keeps shared research history in [the curation log](docs/CURATION-LOG.md), including duplicates and deferred leads.

Use this prompt from the repository:

> Use $jev-curator to browse recent Jev work on X and GitHub in Edge. Continue from the curation log, prepare up to three worthwhile directory drafts, verify sources and creator credits, and report what is ready. Do not publish this pass.

If an agent does not discover repository skills automatically, tell it to read `.agents/skills/jev-curator/SKILL.md` directly. For a scheduled run, use the same prompt with an explicit cadence, effort limit, and whether publication is authorized. No schedule is created by these files.

## Name and domain

The selected name is **Jev Directory**: a direct description of the site and its initial scope. The user connected **jev-directory.com**, which serves the site over HTTPS. Production uses `https://jev-directory.com` as its canonical origin. Separate Vercel preview builds retain `noindex`.

Local repository: `E:\jev-directory`. Use `jev-directory` for the package name and any future remote repository name. Keep the origin configurable for local development and deployment previews.
