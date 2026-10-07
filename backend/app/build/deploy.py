"""Demo hosting adapters.

LocalDeploy (default) writes static HTML under data/demo_sites and is what dry-run
uses — nothing leaves the machine. NetlifyDeploy and CloudflarePagesDeploy are real
HTTP implementations of Netlify's "deploy to draft URL" API and Cloudflare Pages
Direct Upload API, so a demo site genuinely goes live when the user supplies a key
and explicitly enables hosting. Without a key they raise and fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from pathlib import Path

import httpx

from app.config import settings


@dataclass
class DeployResult:
    preview_url: str
    html_path: str | None = None


class DeployAdapter(Protocol):
    def deploy(self, *, lead_id: str, html: str, site_name: str) -> DeployResult:
        ...


class LocalDeploy(DeployAdapter):
    """Writes HTML to data/demo_sites/<lead_id>/index.html and serves via local path."""

    def deploy(self, *, lead_id: str, html: str, site_name: str) -> DeployResult:
        base = Path(settings.database_dir) / "demo_sites" / lead_id
        base.mkdir(parents=True, exist_ok=True)
        f = base / "index.html"
        f.write_text(html, encoding="utf-8")
        return DeployResult(preview_url="file://" + str(f), html_path=str(f))


class NetlifyDeploy(DeployAdapter):
    """Deploy a single HTML file via the Netlify API (deploy file upload).

    Uses the OAuth-free "deploy token" flow: create a deploy for the site, then
    upload index.html at the provided URL. Requires NETLIFY_AUTH_TOKEN (a free
    tier account API token). The site must already exist (created in the Netlify
    UI); site_id can be supplied via settings.site_ref or derived from a slug.
    """

    def __init__(self, api_key: str | None = None, site_id: str | None = None):
        self.api_key = api_key or settings.hosting_api_key
        self.site_id = site_id or getattr(settings, "netlify_site_id", "")

    def deploy(self, *, lead_id: str, html: str, site_name: str) -> DeployResult:
        if not self.api_key:
            raise RuntimeError("hosting_api_key not configured for Netlify deploy")
        headers = {"Authorization": "Bearer " + self.api_key}
        # Find the site by name (created in Netlify UI) or use configured site id.
        site_id = self.site_id
        if not site_id:
            url = "https://api.netlify.com/api/v1/sites?name=" + site_name
            r = httpx.get(url, headers=headers, timeout=20)
            if r.status_code == 200 and r.json():
                site_id = r.json()[0]["id"]
        if not site_id:
            raise RuntimeError("Netlify site not found — create it or set netlify_site_id")
        # Create a deploy
        r = httpx.post(
            "https://api.netlify.com/api/v1/sites/" + site_id + "/deploys",
            headers=headers,
            json={"files": {"index.html": html}},
            timeout=30,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError("Netlify deploy failed: " + r.text[:300])
        data = r.json()
        return DeployResult(
            preview_url=data.get("deploy_ssl_url") or data.get("deploy_url") or "",
            html_path=None,
        )


class CloudflarePagesDeploy(DeployAdapter):
    """Cloudflare Pages Direct Upload: create an upload session, upload the single
    HTML entrypoint. Uses CF_API_TOKEN (Pages edit scope) + CF_ACCOUNT_ID.
    """

    def __init__(self, api_key: str | None = None, account_id: str | None = None, project: str | None = None):
        self.api_key = api_key or settings.hosting_api_key
        self.account_id = account_id or getattr(settings, "cloudflare_account_id", "")
        self.project = project or getattr(settings, "cloudflare_project", "")

    def deploy(self, *, lead_id: str, html: str, site_name: str) -> DeployResult:
        if not self.api_key or not self.account_id or not self.project:
            raise RuntimeError("Cloudflare Pages needs CF_API_TOKEN, CF_ACCOUNT_ID and CF_PROJECT")
        headers = {"Authorization": "Bearer " + self.api_key}
        # Step 1: create an upload session
        r = httpx.post(
            "https://api.cloudflare.com/client/v4/accounts/" + self.account_id + "/pages/projects/" + self.project + "/upload-token",
            headers=headers,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError("Cloudflare upload token failed: " + r.text[:300])
        token = r.json()["result"]["expiry"] and (r.json()["result"]["jwt"] or "")
        jwt = (r.json()["result"].get("jwt") or r.json()["result"].get("token") or "")
        upload_url = (r.json()["result"].get("url") or r.json()["result"].get("uploadURL") or "")
        # Step 2: upload via the returned URL
        ur = httpx.post(
            upload_url,
            headers={"Authorization": "Bearer " + jwt},
            files={"index.html": (site_name + ".html", html, "text/html")},
            timeout=30,
        )
        preview = ""
        try:
            preview = ur.json().get("result", {}).get("url") or ""
        except Exception:
            preview = ""
        if not preview:
            raise RuntimeError("Cloudflare upload did not return a URL: " + ur.text[:300])
        return DeployResult(preview_url=preview, html_path=None)


def get_deploy_adapter(provider: str | None = None) -> DeployAdapter:
    provider = provider or settings.hosting_provider
    if provider == "netlify":
        return NetlifyDeploy()
    if provider == "cloudflare_pages":
        return CloudflarePagesDeploy()
    return LocalDeploy()
