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

## Phase 6 — Real acceptance (DONE)
Live, no-mock run on a real Singapore/Queenstown/dentist campaign (P6-Real-Queenstown-Dentist) with
real Ollama (qwen2.5:3b) + real OSM/Overpass. Evidence captured in dashboard/e2e/p6-*.png and the new
dashboard/e2e/p6-acceptance.spec.ts.

- Run view per-stage counts (latest run record 901baa03): discover 11, enrich 1, profile 1, demo 1,
  draft 1, send 0 — every stage executed live; discovery found 15 places, 11 without a website,
  11 inserted (per-source detail: 3 with phone, 1 with email). First trigger hit a transient Overpass
  mirror failure and the run/UI reported it honestly (found 0 + plain-language reason) — re-ran clean, no mocks.
- llm_calls transparency fix (found during acceptance): modify `resolve_llm` to pass `db` (and set
  `purpose="profile"`) into `LLMService` so every pipeline generation is recorded; `build_profile` now
  tags `llm.lead_id` so the call links to the lead. AI activity page now shows real profile calls with
  provider `ollama`, model qwen2.5:3b, latency ms, prompt + response, ok/error status. New test
  `test_resolve_llm_records_generation_to_llm_calls` locks this in.
- Real Ollama prompt fix: local qwen was echoing the JSON-Schema envelope ({type/required/properties})
  instead of plain profile JSON. `OllamaLLM.generate` now shows a plain-JSON example with real content
  shapes + defensively unwraps schema-envelope responses. Profile, demo and draft now succeed on first try.
- Demo: real OSM lead "Dover Dental Surgery" → generated HTML under
  backend/data/demo_sites/<lead_id>/index.html, served at the stable URL
  http://127.0.0.1:8000/demos/dover-dental-surgery-91293283/ (status: live, theme "Comfort and Excellence").
- Drafted email: subject "Quick idea for Dover Dental Surgery" — status draft, sent_at None,
  provider_message_id None (nothing sent). `force_dry_run: true` confirmed.
- Health kept green: 74 pytest (was 73, added 1), dashboard tsc --noEmit exit 0, full e2e 1-pass on the
  new spec (screenshots ~34–131 KB each).

## Phase 7 — production-quality outreach (IN PROGRESS)
Workstream A — data hygiene (DONE)
- .gitignore already covered evidence/, dashboard/qa-artifacts/, dashboard/e2e/p6-*.png,
  backend/data/, *.db, .env; added explicit outbox/ + backend/data/outbox/. Confirmed:
  0 tracked files under evidence/, no tracked p6-* images.
- New pre-commit gate (alongside gitleaks): scripts/check_contact_data.py +
  backend/app/core/data_hygiene.py. Fails when any staged text blob contains a
  real-looking email/phone (allowlist: example.com/org/net + subdomains, *.test,
  *.invalid, +65 0000 / 555-01xx fake numbers, YYYYMMDD model ids/dates) and when a
  staged image is under /evidence or named p6-*. Hook reinstalled with python resolved.
- Test: backend/tests/test_data_hygiene.py (24 cases: email/phone allowlist, adversarial
  invented-service/price/phone/email blocks).
- Audit scan: `git ls-files` (140 tracked) + scanner found REAL-looking fixture
  data in committed files (reset_db seed phones, test emails/phones, .env.example
  examplesend.com). No rewrite of history — these were replaced with allowlisted
  fakes in the working tree (re-staged) and committed here. New scanner + test lock
  the gate so nothing real gets in again. Tracked p4/p5 dashboard e2e PNGs are UI
  screenshots of the console (not lead/evidence images) and stay tracked.
- Health: pytest 98 · dashboard tsc exit 0.
Workstream B — grounded content (done)
- VerifiedFact model (backend/app/models/verified_fact.py) + collection in
  backend/app/core/facts.py. Only discovery/enrichment/human-sourced facts become
  verified facts; generated copy is never written back as a fact. Each fact has
  field, value, source, timestamp. Table auto-created by Base.metadata.
- LLM prompts receive ONLY verified facts (jobs/profile.py); services and
  selling_points must be JSON tagged {text, kind, source_fact_id}. kind=verified
  requires a real fact id and matching value; kind=generic is restricted to a
  neutral allowlist (backend/app/core/claims.py: retry up to 2 with violations
  listed, then deterministic fallback with no unverified claims).
- Deterministic claim validator (backend/app/core/claim_validator.py) rejects
  invented services, prices, years, awards, certifications, payments, equipment,
  staff, testimonials, rankings, patient counts, guarantees and superlatives
  unless grounded in a verified fact. Same validator reused for email drafts and
  call scripts (Workstream H wiring).
- Tests: backend/tests/test_grounded_content.py — 14 adversarial cases: invented
  services/awards/payments/testimonials/superlatives all blocked; generic phrases
  pass; verified grounding passes; unknown fact ids rejected; retry + feedback +
  fallback verified; validator deterministic.
- Health: pytest 115 (was 101) · dashboard tsc unchanged.
Workstream C — demo site quality (done)
- Rewrote backend/app/build/templates.py: 8 category-aware theme packs
  (clinical, salon, cafe, boutique, repair, education, fitness, generic), each
  with its own palette, system-font stack (no webfonts), hero style and inline
  SVG icon set. Single responsive page, noindex, no scripts/tracking/external
  requests, < 100KB, skip-link + focus-visible + AA-ish contrast + reduced-motion.
- Page structure per spec: sticky header w/ Call + WhatsApp when a phone exists,
  hero (tagline + primary/secondary CTA), Services cards (only verified or
  generic phrasing, else clearly-labelled "Sample content"), About, Why choose
  us, Opening hours when known, Location + "Open in Google Maps" link, Contact
  from verified contacts only, footer with "Demo preview by <sender>" identity
  + Request removal link. No placeholder sender email on the page; placeholder
  sender identity shows a generic notice instead (lead not marked live-ready).
- backend/app/jobs/build_demo.py now reads verified facts (phone/email/
  opening_hours) for the page, persists theme across regenerations, and is
  idempotent on demo_ready. Theme override supported for per-lead switching.
- Demo management endpoints (backend/app/api/routers/demos.py): POST
  /{lead_id}/delete, GET /{lead_id}/build_log (facts used + expiry), PATCH
  /{lead_id}/theme (switch + regenerate). demo_expired() = 30-day auto-expiry.
- Tests: backend/tests/test_demo_theme.py — 12 tests (theme pack count/mapping,
  required sections, phone/WA/email contact buttons, placeholder identity,
  page weight, no external requests, plus endpoint tests for delete/build_log/
  theme switch/unknown theme/expiry). Health: pytest 127 (was 115).

