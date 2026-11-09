# JevMatch

A Manifest V3 browser extension that scores the fit between your resume and a
job posting — initially on LinkedIn. Backendless: the browser talks directly
to TypeSafe's Jev (System One) API.

Jev is used as a **probabilistic decision engine**, not a generative LLM. It
answers small typed questions (Choice / Score / Noul); the final score,
missing-skill list, and blocker decisions are computed deterministically in
TypeScript.

## How it works

1. You save your resume (paste or local PDF extraction) and your TypeSafe API
   key in the options page.
2. On a LinkedIn job page, open the JevMatch popup and click **"Check this
   job"**. (Analysis is on-demand only — nothing runs automatically while
   you browse; see "Manual vs. automatic checking" below.) The content
   script extracts the visible job description and asks the background
   service worker for an analysis, then renders the result as an in-page
   panel.
3. The service worker sends **one** `POST /v1/systemone` request with an
   object state `{ resume, job }` and independent questions:
   - `seniorityFit` (Score), `roleFit` (Score)
   - per detected skill (local catalog, ≤12): `<skill> requirement` (Choice:
     required / preferred / not_required) and `<skill> evidence` (5-level Score)
   - relevant hard blockers (Noul): spoken language, location/on-site, work
     authorization, mandatory certification
4. TypeScript computes the result:
   - **55%** technical (evidence weighted: required ×1, preferred ×0.5)
   - **30%** seniority, **15%** role/domain fit
   - Missing required skills = `required` with normalized evidence < 0.4
   - Triggered blockers render as a banner and are never hidden by the score
   - Jev `confidence` (Choice/Score only) becomes a High / Medium / Review
     badge — a review signal, never multiplied into the score

Results are cached per resume+job hash in session storage.

## Manual vs. automatic checking

The MVP only runs analysis when you click **"Check this job"** in the popup
— it does not watch the page or re-run automatically as you browse listings.
This keeps API usage predictable and avoids surprise requests.

The automatic-detection code (SPA navigation watcher + re-analyze on job
change, `src/content/job-observer.ts`) is still implemented and wired up
behind a flag: flip `AUTO_CHECK` to `true` in `src/content/index.ts` to
re-enable it. The popup's manual trigger (`chrome.tabs.sendMessage` with
`{ kind: 'CHECK_CURRENT_JOB' }`) works either way.

## Security model

- The content script never receives the API key or the resume — only the
  computed `MatchResult`.
- The service worker calls `chrome.storage.local.setAccessLevel(
  'TRUSTED_CONTEXTS')` at startup so extension storage is not readable from
  content scripts. The key can optionally be kept session-only
  (`chrome.storage.session`).
- Minimum permissions: `storage`, `activeTab` (used only to message the
  content script when you click "Check this job" in the popup — it doesn't
  grant standing access to LinkedIn), `host_permissions` for
  `api.typesafe.ai`, and a content script scoped to `linkedin.com/jobs/*`.

**Honest limitation:** a BYOK key stored in a browser extension is not
cryptographically secure against someone with access to your machine or
browser profile. These measures prevent unnecessary exposure to pages, the
DOM, and content scripts — nothing more.

## Develop

```bash
npm install
npm run dev        # vite dev with HMR (load dist/ unpacked)
npm run build      # production build to dist/
npm test           # vitest: scoring, detection, questions, client
npm run typecheck
```

Load `dist/` at `chrome://extensions` (Developer mode → Load unpacked).

## Troubleshooting

**Console shows repeated `GET chrome-extension://invalid/... net::ERR_FAILED`
from `window.fetch`.** This is not an app bug — it means the tab has a
*stale* content script. CRXJS content scripts are tiny ES-module loaders that
call `chrome.runtime.getURL(...)` to dynamically import the real script. If
you reload the extension at `chrome://extensions` (or restart `npm run dev`)
while a LinkedIn tab is already open, that tab's old content script instance
is left with a detached `chrome.runtime` — `getURL()` then returns
`chrome-extension://invalid/...` and every import fails, repeating on every
SPA navigation.

Fix: after **every** extension reload, close the LinkedIn tab and open a
fresh one (or hard-refresh with Ctrl+Shift+R) before testing again. For
iterative testing, prefer `npm run build` + manual reload over `npm run dev`
— it removes the extra HMR client/port code path and is easier to reason
about when debugging.

**Panel never appears / no `[jevmatch]` logs at all.** The content script
never ran. Check: extension enabled and pointed at `dist/`; the tab was
opened/refreshed *after* the last reload; the URL matches
`https://www.linkedin.com/jobs/*` (job search results pages like `/jobs/`
without `/jobs/...` path segments won't match — click into a job listing).

**Logs show extraction retries exhausting, `no-job` panel shown.** Selectors
didn't match. Open the panel's browser console, note which candidate texts
(if any) were found and their lengths, and update
`src/content/sites/linkedin/selectors.ts` accordingly — LinkedIn's markup
varies between the logged-in "unified" UI and the public/guest view.

## Notes & limitations

- LinkedIn is an SPA with frequently-changing markup; all selectors live in
  `src/content/sites/linkedin/selectors.ts` as fallback chains.
- The extension only reads the DOM of pages you already opened. No
  automation, pagination, or scraping. Use subject to LinkedIn's terms.
- Jev's primary training language is English; non-English resumes/job posts
  currently get lower accuracy.
- Chrome/Edge (MV3) first; Firefox packaging is a non-goal for the MVP.
