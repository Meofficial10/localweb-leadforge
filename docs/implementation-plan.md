# Implementation Plan — LeadForge

Build milestones in order, one at a time. Run tests and summarize after each.

| # | Milestone | Scope | ETA |
|---|---|---|---|
| M0 | Foundation | Repo, docker-compose, DB migrations, settings, auth, logging | 2d |
| M1 | Discovery | Places + OSM adapters, no-website filter, dedupe, scheduler | 3d |
| M2 | Enrichment | Public page fetcher, email/phone extraction, source tracking, classification | 4d |
| M3 | Profile + Demo | LLM adapter, profile schema, 4 theme templates, deploy (Cloudflare/Netlify) | 5d |
| M4 | Compliance core | Suppression, caps, windows, kill switch, audit log, unsubscribe page | 3d |
| M5 | Email outreach | Drafting with fact validation, dry-run, SMTP/Brevo sender, warm-up, reply/bounce tracking, follow-up | 5d |
| M6 | Dashboard | Overview, campaigns, leads, queue, inbox, compliance, settings | 6d |
| M7 | Voice outreach | DNC adapter, call scripts with AI disclosure, provider adapter, webhooks, outcome logging | 5d |
| M8 | Hardening | Tests, retries/dead letters, alerts, budget caps, docs | 4d |
| M9 | Pilot | One city, one category, 20 emails/day live; weekly review | 2wk |

## Rollout
- Week 1-2: dry-run only, review drafts and demo quality.
- Week 3: live email at 10-20/day, watch bounce/complaint rates.
- Week 4+: raise caps gradually; add follow-ups.
- Later: voice calls only for DNC-cleared numbers, starting with a handful per day.

## Free-tier notes
See README-setup.md. Every paid integration has a free or local alternative. AI voice carriers only have trial credits; ask before enabling voice in any real volume.
