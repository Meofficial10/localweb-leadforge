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
- Dashboard demo sites page (dashboard/app/demos/page.tsx): table (lead, theme select -> PATCH /demos/{id}/theme, status incl expired, hosting Local/Deployed, size kB, created) with actions Open / Regenerate / Build log (verified facts used) / Delete; loading+empty+error states.
- Visual QA (Playwright, 8 themes x 390+1440px = 16/16 pass): no h-scroll, all sections + hero + inline SVG icons + CTAs, no unverified claims, no placeholder sender, page weight < 7 KB; screenshots only under evidence/ (gitignored). Repro: dashboard/qa-demos.cjs + evidence/demo-paths.tsv.


## Phase 7-D: production-ready outreach - pipeline coverage, per-contact-type drafts, enrich + reasons

Fix for "only 1 of 11 leads processed": the pipeline advanced every lead by exactly one stage
per run, and enrichment discarded contact data already present at discovery (OSM/Google contact:*/
phone/email) so most leads stalled. Changes:
- Discovery now persists contacts + contact_type at insert time (backend/app/jobs/discovery.py):
  OSM phone/email become Contact rows with a provenance source_url (OpenStreetMap element link /
  maps.google.com cid), E.164-normalized (normalize_phone) so no-website leads with contact are
  ready for profile -> demo -> draft in the SAME run, not after several runs.
- Enrichment (backend/app/enrichment/service.py) no longer returns early for leads that already have
  contacts: it classifies them and transitions discovered -> enriched so they advance. Candidate URLs
  now include OSM social tags (contact:facebook/instagram/twitter). No-contact leads transition via
  state machine discovered -> no_contact (new legal transition in app/core/state_machine.py) with
  no_contact_reason + enrichment_sources (URLs tried) persisted on the lead.
- Pipeline (backend/app/jobs/pipeline.py): per-lead loop now advances each lead through ALL stages
  in one run (discover -> enrich -> profile -> demo -> draft). Drafts are contact-type aware:
  email -> email draft (existing prepare_email_message); phone-only -> WhatsApp/text short draft +
  call-script draft, both with AI disclosure + DNC status; no-contact -> terminal no_contact with
  reason + sources tried. Run summary adds no_contact + queued_call counts and per-reason tally
  (summary.reasons) on top of per-stage counts.
- Jobs/enrichment.py returns per-reason no_contact breakdown for the run summary.
- Migration d1e2f3a4b5c6 adds leads.no_contact_reason + leads.enrichment_sources (nullable).
- Tests: backend/tests/test_pipeline_coverage.py - 6 tests (discovery persists contacts & type,
  enrichment transitions pre-seeded contacts & records reason/sources, one-run full cascade, phone
  draft AI+DNC disclosure, per-stage+per-reason summary). Also realigned test_placeholder_sender_identity
  in test_demo_theme.py to assert the actual placeholder behavior (example sender not shown as identity).
  Health: pytest 133 (was 127). Dashboard tsc 0. import app.main OK.

## Phase 7-E: email draft quality - grounds drafts in verified facts via shared validator

Assumption: E-I scope inferred from the implementation plan (M5 email outreach, M7 voice, M8
hardening) + the Workstream B note that the claim validator is 'reused for email drafts and call
scripts'. E = email draft grounding; F-G = queue/send + follow-up hardening; H = voice wiring.

- backend/app/outreach/email/draft.py: validate_facts() now runs every claim-bearing sentence
  of the email body through the Workstream B deterministic validator (claim_validator.
  validate_claims) against the lead's verified facts. Outreach mechanics (demo page, reply, stop)
  are stripped before vetting so they never count as business claims. A draft that references an
  invented service/price/award/year/testimonial/superlative raises FactValidationError and is
  never queued. draft_email accepts a facts parameter (backward compatible).
- backend/app/jobs/send.py prepare_email_message() collects the lead's verified facts
  (collect_verified_facts) and passes them into draft_email, so every email draft is grounded.
- backend/app/core/claim_validator.py: broadened price pattern to catch plurals (price/prices) and
  added implants to the equipment pattern (dental 'dental implants' is now an unverifiable claim
  unless a verified fact says so).
- Workstream B tests still green (14/14); email drafts comply with the guided style (<120 words,
  business first line, one link, opt-out line).
- Tests: backend/tests/test_draft_grounding.py - 4 tests (grounded template passes word/opt-out
  checks + stays under 120 words; invented superlative/patient-count blocked; clean mechanics
  pass; monkeypatched template injecting 'dental implants at affordable prices' is rejected).
  Health: pytest 137 (was 133).

## Phase 7-F: queue/outbox dry-run send path hardening (M5 send + F scope)

- backend/app/jobs/send.py send_message(): the compliance gate is always checked and
  fails closed (suppression / rate caps / DNC keep blocking). The Workstream F
  hardening: when dry-run is active (global force_dry_run or campaign mode dry_run)
  the 'channel in dry-run mode' reason is not fatal - the send routes to the local
  file outbox (FileSender), the safe sink that cannot reach a recipient - and any
  caller-supplied real provider adapter is FORCIBLY replaced by FileSender so a
  stray SMTP/Brevo instance can never fire during a dry-run queue. Live sends still
  require an explicit adapter and a live-shape compliance pass.
- backend/app/api/routers/queue.py: added GET /queue/outbox - lists messages with
  status=sent and the provider sink id (file:...) so the dashboard can show what a
  dry-run queue would have delivered, plus POST /queue/{message_id}/send - the
  hardened dry-run send path for approved/queued email drafts (409 on drafts).
- Tests: backend/tests/test_send_path.py - 7 tests (approved dry-run goes to file
  outbox and marks sent + transitions to contacted; draft/skipped not sendable;
  suppression blocks; a caller SMTP adapter is never fired in dry-run; live mode
  uses the passed sender; outbox listing surfaces sent records; send endpoint
  rejects unapproved). pytest 144 (was 137).

## Phase 7-G: follow-up + reply/bounce tracking

- backend/app/jobs/send.py schedule_followup(): follow-up is now a SCHEDULED draft
  carrying scheduled_at = now + days_delay (default 4). It is never sent
  immediately, and it returns None when the lead is not contacted, already has a
  step-2 draft, or has replied/opted out - no stacking follow-ups.
- cancel-on-response: backend/app/api/routers/webhooks.py tracks replies, bounces
  and opt-outs and marks any pending step-2 follow-up draft as cancelled (status
  'cancelled') instead of leaving it to fire later. Keeps the first-touch message
  untouched. Same for unsubscribe (_cancel_pending_followups).
- Bounce tracking was already wired (msg.bounced + state + auto-pause stats);
  reply tracking sets lead status replied + parent message replied + inbound
  message created with an intent label (interested / question / opt_out /
  not_interested / neutral) for the inbox.
- Tests: backend/tests/test_followup_tracking.py - 6 tests (deferred + scheduled_at;
  followup only once; no follow-up after reply; reply webhook cancels pending
  follow-up + transitions lead/parent to replied; bounce webhook sets bounced +
  cancels pending follow-up + updates auto-pause stats; unsubscribe suppresses +
  cancels + opts out. pytest 150 (was 144).

## Phase 7-H: voice call-script + DNC adapter wiring

- backend/app/core/dnc.py: new get_dnc_registry() resolver + RegistryDNCCheck HTTP
  adapter. 'none' (default) stays fail-closed (NoDNCCheck - every call blocked);
  'registry' hits {base}/check?phone=... with the API key and fails CLOSED on any
  error/timeout/missing key (num not on registry -> 200 = clear; 404/410/HTTP err).
- backend/app/config.py: dnc_registry_base_url setting (mirrors the catalog).
- backend/app/jobs/voice.py place_call_for_lead(): default compliance now resolves
  the DNC registry from settings (force_dry_run also passed through), and the
  provider is pinned to MockVoiceProvider whenever dry-run is active (global
  force_dry_run, voice_dry_run, or campaign mode dry_run) - a caller-passed real
  adapter can never fire during a dry-run queue. Non-dry-run uses get_voice_provider().
- Tests: backend/tests/test_voice_dnc.py - 5 tests (no phone; dry-run default blocks;
  DNC registry blocks a registered number with zero Call rows; dry-run pins mock even
  with a caller-passed real adapter; full live path records the Call row with
  ai_disclosed + transitions to contacted). pytest 155 (was 150).
