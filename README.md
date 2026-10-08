# LeadForge

An automated lead-generation and outreach system for local businesses with **no website**. LeadForge discovers them, builds each one a **demo website**, and runs compliance-gated outreach by **email** or **AI voice call**.

> **Every outbound channel defaults to DRY-RUN.** The system discovers, enriches, profiles and builds demo sites, and drafts outreach — but sends nothing until you explicitly enable LIVE mode per channel.

## Run the project (one command)

The repo ships a root-level runner so you can start **backend + dashboard together** with one command — no manual venv activation needed.

Prerequisites: **Node.js 18+** (with npm) and **Python 3.12**.

```bash
# First time only: create the backend venv, install backend + dashboard deps,
# copy .env.example -> backend/.env if missing, and apply Alembic migrations.
npm run setup

# Development (hot reload) — backend on :8000, dashboard on :3006
npm run dev            # or: scripts\dev.ps1   (Windows)  /  bash scripts/dev.sh

# Production — builds the dashboard then serves it (backend without --reload)
npm run start

# Reset the database (drop + recreate; add --seed for demo data)
npm run reset          # python -m scripts.reset_db
npm run reset -- --seed
```


## Performance notes (M5)

- **Use `npm run start` (or `next start`) for everyday use.** `next dev` compiles on
  demand and is noticeably slower for page loads; the production build is pre-compiled.
- **Overview loads in a single request.** `/system/overview` returns metrics, effective
  mode, caps and recent audit together, cached in-process for ~5s.
- **List endpoints are server-paginated + filterable** — `/leads`, `/messages`,
  `/system/audit` support `page`/`page_size`, `status`, `channel`/`lead_id` filters
  (leads also `campaign_id`, `category`, `search`, `sort`). The console never fetches
  full tables client-side.
- **Queries are cached with TanStack Query** (`staleTime`, no window-focus refetch);
  the geo dataset for the campaign wizard is lazy-fetched per country once.
- **Indexes** cover the hot paths: `leads.status`/`campaign_id`, `messages.lead_id`/
  `status`, `jobs.stage`/`status`, `audit_log.created_at` (migration
  `c52d1e9a0b11`).
- **Run polling is bounded**: active Apify runs are polled only while `running`/
  `queued`, on a 3–5s interval, and the poll stops once the run reaches a terminal
  state (`done`/`failed`).
**What `npm run dev` starts:**

| Prefix | Process | URL |
|--------|---------|-----|
| `[api]` | FastAPI (uvicorn --reload) via `backend/.venv` | http://127.0.0.1:8000/docs |
| `[web]` | Next.js 15 dashboard | http://127.0.0.1:3006 |

`scripts/dev.ps1` (Windows) and `scripts/dev.sh` (macOS/Linux) are thin launchers
that run the same `npm run dev` flow and automatically run `setup` first if the
venv or dashboard `node_modules` are missing.

> The dashboard shows a **"Backend not reachable at …" banner with a Retry button**
> whenever the API at `http://localhost:8000` is down, so a mis-started backend is
> obvious instead of showing confusing errors.

## Why this exists
Small local businesses often have no web presence, yet cold outreach is slow, generic, and manual — and high-volume outreach without compliance controls gets accounts banned and runs afoul of Singapore's Spam Control Act / PDPA, plus CAN-SPAM and GDPR. LeadForge automates discovery → enrichment → profile → demo site build → personalized email / AI call → reply tracking → human handoff, with compliance gates, daily caps, suppression, and dry-run defaults built in.

## Monorepo layout
```
/backend    FastAPI + SQLAlchemy + Alembic (Python 3.12)
/dashboard  Next.js + Tailwind operator console
/infra      docker-compose (backend + Postgres + dashboard)
/docs       backend-schema.md, implementation-plan.md, design brief, setup guide
```

## Quick start (local, SQLite, dry-run)
```bash
cd backend
python -m venv .venv
# activate on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp ../.env.example .env
alembic upgrade head
pytest
uvicorn app.main:app --reload
# open http://localhost:8000/docs
```

Then open the dashboard:
```bash
cd dashboard
npm install
npm run dev
# open http://localhost:3000
```

## Dry-run mode
Outbound email and voice are DRY-RUN by default. In dry-run:
- Leads are discovered, enriched, profiled, demo sites are generated.
- Emails are drafted with status `draft` (subject + body, fact-checked). Nothing leaves the server, no SMTP send occurs, no `.eml` is written to the box (the file sink is only used when you switch the email channel to live with `FILE_SINK` semantics).
- No call is placed; the voice adapter returns a canned transcript.

To go live, per channel, the operator must explicitly set the channel/campaign to LIVE and the global `FORCE_DRY_RUN` must be `false`. The compliance gate still applies in full either way.

## Compliance architecture
- **Single gate** `app/core/compliance.py` `ComplianceService.check()` runs before every outbound email or call, fail-closed.
- **Global suppression** (`app/core/suppression.py`): unsubscribe / stop is honored instantly and permanently, by exact email, phone, or domain.
- **Singapore DNC**: call/text is blocked unless a DNC check completes; if the check itself is unavailable the gate **fails closed** (`app/core/dnc.py`).
- **Frequency caps**: daily caps per channel, per-domain throttle, warm-up ramp (`app/core/rate_limiter.py`).
- **Call hours**: configurable window (default 10:00–18:00 weekdays).
- **Auto-pause**: bounce rate >5% or complaint spikes pause the channel (`webhooks` → `stats.*` → `compliance`).
- **Kill switch**: global + per-channel pause via `/system/pause`, `/system/status`.
- **Audit log**: every message/call recorded (`audit_log`), browsable at `/system/audit`.
- **Data deletion**: `DELETE /leads/{id}` plus suppression as the instant opt-out path.
- **AI disclosure**: every outbound call script carries AI-voice disclosure; configurable sender identity.
- **Spam Act / CAN-SPAM**: physical address + real unsubscribe link in every email; dry-run default.

## Tests
```bash
cd backend && pytest
```
Covers: state machine, suppression, rate limiter, compliance gates, contact extraction, discovery dedupe, full dry-run pipeline, and API smoke tests (all against isolated in-memory SQLite).

## Free-tier stack
| Concern      | Choice                          |
|--------------|---------------------------------|
| Lead sources | Google Places API (official, key required), OSM Overpass fallback |
| LLM          | Ollama local (default, free), OpenAI/Anthropic via API key |
| Demo hosting | Local static (default), Cloudflare Pages / Netlify API |
| Email        | SMTP (free), Brevo / Resend free tiers, or local file sink |
| Voice        | Vapi / Retell / Bland adapter (DRY-RUN by default) |
| DB           | PostgreSQL 16 (prod via docker-compose), SQLite (local) |
| Queue        | APScheduler in-process (v1)      |
| Auth         | Bearer token (header `Authorization: Bearer <AUTH_TOKENS>`) |

Source adapters never scrape Google Maps HTML — only official APIs (Places TextSearch + Details) and the OSM Overpass API.

## Docs
- `docs/backend-schema.md` — full relational schema the Ale order & Alembic migration implement.
- `docs/implementation-plan.md` — milestones M0–M9 with acceptance tests.
- `docs/design-brief.md` — product + compliance decisions.
- `docs/README-setup.md` — per-provider free-tier setup.
