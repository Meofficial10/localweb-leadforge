# Backend Schema — LeadForge

PostgreSQL in production, SQLite for local dev. These names are canonical and must match the Alembic migrations.

## campaigns
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | TEXT | |
| country | TEXT | default "Singapore" |
| city | TEXT | |
| categories | TEXT[] | e.g. salon, cafe, repair, florist |
| daily_email_cap | INT | default 20 |
| daily_call_cap | INT | default 10 |
| send_window | JSONB | call hours / days window |
| mode | TEXT | dry_run (default) | live |
| is_paused | BOOL | kill switch per campaign |
| created_at | TIMESTAMPTZ | |

## leads
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| campaign_id | UUID FK | |
| source | TEXT | places | osm | ... |
| source_place_id | TEXT | dedupe key |
| name | TEXT | |
| category | TEXT | |
| address | TEXT | |
| lat / lng | NUMERIC | |
| rating | NUMERIC | |
| review_count | INT | |
| has_website | BOOL | default false (discovery filter) |
| contact_type | TEXT | email | phone | both | none |
| status | TEXT | state machine, default "discovered" |
| created_at / updated_at | TIMESTAMPTZ | |
| UNIQUE (source, source_place_id) | | |

## contacts
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| lead_id | UUID FK CASCADE | |
| kind | TEXT | email | phone | website |
| value | TEXT | |
| source_url | TEXT | every contact must have one |
| verified | BOOL | |
| found_at | TIMESTAMPTZ | |
| UNIQUE (lead_id, kind, value) | | |

## profiles
| Column | Type | Notes |
|---|---|---|
| lead_id | UUID PK FK CASCADE | |
| summary | TEXT | |
| services | JSONB | |
| tone | TEXT | |
| selling_points | JSONB | |
| brand | JSONB | colors, theme file |
| raw_inputs | JSONB | inputs sent to LLM |
| created_at | TIMESTAMPTZ | |

## demo_sites
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| lead_id | UUID FK CASCADE | |
| template | TEXT | theme pack id |
| html_path | TEXT | local file path |
| preview_url | TEXT | hosted URL |
| deploy_status | TEXT | draft | deploying | live | failed |
| version | INT | default 1 |
| created_at | TIMESTAMPTZ | |

## messages
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| lead_id | UUID FK CASCADE | |
| channel | TEXT | email | voice followup |
| direction | TEXT | outbound | inbound |
| sequence_step | INT | default 1 |
| subject / body | TEXT | |
| status | TEXT | draft | queued | approved | sent | failed | replied | opted_out | bounced |
| provider_message_id | TEXT | |
| scheduled_at / sent_at | TIMESTAMPTZ | |
| opened_at | TIMESTAMPTZ | |
| bounced | BOOL | |
| intent | TEXT | interested | not_interested | ... |

## calls
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| lead_id | UUID FK CASCADE | |
| provider_call_id | TEXT | |
| dnc_checked_at | TIMESTAMPTZ | |
| ai_disclosed | BOOL | default true (mandatory) |
| started_at | TIMESTAMPTZ | |
| duration_sec | INT | |
| outcome | TEXT | |
| transcript | TEXT | |
| recording_url | TEXT | |
| recording_consent | BOOL | default false |

## suppression_list
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| kind | TEXT | email | phone | domain |
| value | TEXT | |
| reason | TEXT | |
| created_at | TIMESTAMPTZ | |
| UNIQUE (kind, value) | | |

## jobs
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| lead_id | UUID | |
| stage | TEXT | discover | enrich | profile | build | draft | send | call | followup |
| status | TEXT | pending | running | succeeded | failed | dead_letter |
| attempts | INT | |
| last_error | TEXT | |
| run_after | TIMESTAMPTZ | retry backoff |
| updated_at | TIMESTAMPTZ | |

## audit_log
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL PK | |
| lead_id | UUID | |
| actor | TEXT | system | user | worker |
| action | TEXT | send_email | place_call | suppress | ... |
| detail | JSONB | |
| created_at | TIMESTAMPTZ | |

## settings
| Column | Type | Notes |
|---|---|---|
| key | TEXT PK | |
| value | JSONB | |

Indexes: leads(status), messages(lead_id, channel), jobs(stage,status,run_after).

## Key API endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | /campaigns | create campaign |
| POST | /campaigns/{id}/run | trigger discovery run |
| GET | /leads | list leads (filters) |
| GET | /leads/{id} | lead detail (profile, demo, timeline) |
| POST | /leads/{id}/demo/regenerate | rebuild demo |
| POST | /messages/{id}/approve | approve a draft |
| POST | /webhooks/email | bounce/open/reply events |
| POST | /webhooks/voice | call outcome events |
| GET | /u/{token} | public unsubscribe |
| POST | /system/pause | global kill switch |
| DELETE | /leads/{id} | data deletion |
