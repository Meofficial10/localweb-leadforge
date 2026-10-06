"""Public page fetcher respecting robots.txt and rate limits.

Only public pages are fetched (listing pages, Facebook/Instagram About pages,
directory pages). Does not touch login-gated content. A robots.txt check is done
per domain and negative results are cached for the session.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from urllib.robotparser import RobotFileParser

import httpx
from urllib.parse import urljoin

from app.logging_conf import get_logger

logger = get_logger(__name__)

ALLOWED_HOSTS_PREFIXES = ("facebook.com", "instagram.com", "linkedin.com")
_BLOCKED_EXT = (".pdf", ".jpg", ".png", ".gif", ".mp4", ".zip", ".exe", ".docx", ".xlsx")


@dataclass
class FetchedPage:
    url: str
    final_url: str
    html: str
    status_code: int
    from_cache: bool = False


class PageFetcher:
    def __init__(self, client: httpx.Client | None = None, delay: float = 0.3):
        self.client = client or httpx.Client(
            timeout=20,
            headers={
                "User-Agent": "LeadForge/0.1 (lead research; respects robots.txt)",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
        )
        self.delay = delay
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_req: dict[str, float] = {}
        self._lock = threading.Lock()

    def _allowed(self, url: str) -> bool:
        if any(url.lower().endswith(ext) for ext in _BLOCKED_EXT):
            return False
        host = httpx.URL(url).host or ""
        if any(host.startswith(p) for p in ALLOWED_HOSTS_PREFIXES):
            # social platforms usually don't enforce robots via these pages
            return True
        rp = self._robots.get(host)
        if rp is None and host not in self._robots:
            try:
                robots_url = urljoin(url, "/robots.txt")
                resp = self.client.get(robots_url, timeout=10)
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
            except Exception:  # noqa: BLE001
                rp = None
            self._robots[host] = rp
        if rp is None:
            return True
        return rp.can_fetch("LeadForge/0.1", url)

    def fetch(self, url: str) -> FetchedPage | None:
        try:
            if not self._allowed(url):
                logger.info("robots.txt blocks %s", url)
                return None
            with self._lock:
                host = httpx.URL(url).host or ""
                last = self._last_req.get(host, 0)
                wait = self.delay - (time.time() - last)
                if wait > 0:
                    time.sleep(wait)
                self._last_req[host] = time.time()
            resp = self.client.get(url)
            if resp.status_code != 200:
                return None
            return FetchedPage(
                url=url,
                final_url=str(resp.url),
                html=resp.text,
                status_code=resp.status_code,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch failed %s: %s", url, exc)
            return None
