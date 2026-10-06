"""Demo hosting adapters. Local (writes to a static dir under data/) is the default
and is what dry-run uses. Cloudflare Pages / Netlify adapters are swappable and
only used when HOSTING_PROVIDER is set with a key (paid/free-tier API).
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
        return DeployResult(preview_url=f"file://{f}", html_path=str(f))


class NetlifyDeploy(DeployAdapter):
    def __init__(self, api_key: str | None = None, site_prefix: str = "leadforge-"):
        self.api_key = api_key or settings.hosting_api_key
        self.site_prefix = site_prefix

    def deploy(self, *, lead_id: str, html: str, site_name: str) -> DeployResult:
        if not self.api_key:
            raise RuntimeError("hosting_api_key not configured for Netlify deploy")
        # Netlify "deploy file content" API is used in prod; here we stub the contract.
        # Real impl: create deploy & upload file to /sites/<id_deploy>/functions...
        raise NotImplementedError("NetlifyDeploy requires live API wiring (free tier token)")


class CloudflarePagesDeploy(DeployAdapter):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.hosting_api_key

    def deploy(self, *, lead_id: str, html: str, site_name: str) -> DeployResult:
        if not self.api_key:
            raise RuntimeError("hosting_api_key not configured for Cloudflare Pages deploy")
        raise NotImplementedError("CloudflarePagesDeploy requires live API wiring (free tier token)")


def get_deploy_adapter(provider: str | None = None) -> DeployAdapter:
    provider = provider or settings.hosting_provider
    if provider == "netlify":
        return NetlifyDeploy()
    if provider == "cloudflare_pages":
        return CloudflarePagesDeploy()
    return LocalDeploy()
