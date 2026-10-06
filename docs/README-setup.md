# Provider setup notes (free-tier first)

## Google Places API
- Enable "Places API" in Google Cloud console, create a key.
- Free monthly credit — set a billing alert. Not strictly required: OSM Overpass works with zero keys.

## OSM Overpass (no key)
- Endpoints: https://overpass-api.de/api/interpreter (add mirrors: overpass.kumi.systems).
- Query businesses by tagging around a city radius, filter for missing `contact:website` / `website`.

## Ollama (local LLM, free)
- Install Ollama, `ollama pull llama3.1:8b` (or qwen2.5). 
- Default base URL http://localhost:11434.

## Cloudflare Pages / Netlify
- Create an API token with Pages permissions (Netlify) — free tier.
- Set HOSTING_PROVIDER and HOSTING_API_TOKEN; dry-run uses local static instead.

## Email
- SMTP (your provider), Brevo, or Resend — free tiers.
- DRY-RUN default: no email leaves the box. Use a test inbox first.

## Voice
- Vapi / Retell / Bland trials only. Default VOICE_PROVIDER=mock (logs only, no call). 
- DNC registry check must pass (or be blocked) before any real call.

## DNC (Do Not Call) — Singapore
- DNC_PROVIDER adapter; default "none" → calls are blocked until a provider is configured, per compliance rules.
