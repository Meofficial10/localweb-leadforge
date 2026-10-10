# LeadForge Progress

Running note so work can resume cleanly after interruptions.

## Recovery (after interrupted session)
- Power cut interrupted the session mid-Phase 5. Cleanly resumed — nothing started over, no work discarded.
- Health: backend import OK · alembic check clean (no pending migrations) · pytest 73 passed ·
  next build green · SQLite PRAGMA integrity_check = ok.
- Repaired one corrupted file: dashboard/e2e/qa-p5h.spec.ts (unterminated string literal from the power cut).
- Preserved the Phase 5 diagnostic probes (dashboard/e2e/qa-p5*.spec.ts) + screenshots (dashboard/e2e/p5-*.png).
- Committed as `chore: recover after interrupted session`.

## Phase 0 — discovery finds >0 leads (DONE, commit 8b1a501)
Fix 0-leads discovery with real OSM (verified live end-to-end). Re-verified in Phase 6 with a live
Singapore/Queenstown/dentist/OSM run: query, per-source status, elapsed time, counts, plain-language reason.

## Phase 1 — Run view with live pipeline stages (DONE, commit 790d89a)
Live pipeline dialog (Discover/Enrich/Profile/Demo/Draft/Send) with per-stage counts, progress bar,
persisted run_events log, summary banner, finish toast. Tests: tests/test_run_view.py.

## Phase 2 — LLM transparency (DONE, commits 9b06e61 / 776c5bc / b9265e7)
`llm_calls` table, AI activity page (/ai-activity), Overview AI cards, active model on card, 'coder' model
warning, Playground + custom providers (name, Base URL, API key, model, headers) in the LLM configure drawer.

## Phase 3 — Demo sites (DONE, commit 8349a0a)
`/demos/<slug>/` locally served, Demo sites page (Open / Regenerate / build logs), clear
'Local only' vs 'Deployed' labelling.

## Phase 4 — Truthful statuses (DONE, commit ed7ae50)
'Needs setup' labels on placeholder senders, dry-run email is not 'Connected', onboarding checklist
reflects a real lead source, per-process random access tokens.

## Phase 5 — UI bugs (DONE)
- [x] Root cause: one-character bug = Step* components defined inside `CampaignWizard` → per-keystroke
      remount → focus lost after the first character (reproduced via qa-p5c/p5f/p5h.spec.ts).
- [x] Fix: hoisted StepBasics/Location/Business/Outreach/Review to module scope in
      dashboard/app/campaigns/_components/campaign-wizard.tsx. New regression test
      dashboard/e2e/p5-regression.spec.ts types 30 characters at once into name + description and asserts
      focus is retained (all 31 e2e green; probes now show sameNode:true, focused after every keystroke).
- [x] Location list constrained inside the modal (scroll container bounded + scrollable); Singapore is the
      default country; Queenstown selectable — asserted in p5-regression.spec.ts.
- [x] Theme tokens for chart colors: overview-charts.tsx now wraps charts in `text-primary` and uses
      `currentColor` (resolves theme tokens in SVG) instead of literal `var(--primary)` presentation
      attributes; funnel bars get a real themed fill. Probe: `svgs using var() as literal attr: []`.
- [x] e2e type-check repaired: CJS `require` specs → ESM `import` (qa-ai-activity/drawer/demos),
      removed invalid `page.on("popstate")` (qa-p5f), typed qa-sweep handler params. `tsc --noEmit` clean.
- [x] qa-fixes mock Ollama extended with /api/chat so the 'Connected' probe passes (was 404ing once the
      backend added a real generation step). Full suite: 31/31 e2e + 73 pytest green.

## Phase 6 — Real acceptance (NOT STARTED)
Real Ollama + OSM run with no mocks; counts per stage, screenshots, demo HTML path, one drafted email,
proof nothing was sent.
