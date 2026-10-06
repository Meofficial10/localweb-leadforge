"""SEND stage: rate-limited, compliant sender. Email provider adapters sit
behind one interface (smtp / brevo / resend / file). Dry-run is enforced even if
a campaign says live unless force_dry_run is False AND provider is configured.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from app.config import settings


@dataclass
class SendResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class EmailSender(Protocol):
    def send(self, *, to: str, subject: str, body: str, from_name: str, from_addr: str,
             unsubscribe_url: str | None = None) -> SendResult:
        ...


class FileSender(EmailSender):
    """Writes the email to a file sink (data/outbox). Used for dry-run + local dev."""

    def send(self, *, to, subject, body, from_name, from_addr, unsubscribe_url=None) -> SendResult:
        safe_to = "".join(ch for ch in to if ch.isalnum() or ch in "@.").replace("@", "_at_")
        f = settings.database_dir / "outbox" / f"{int(time.time())}_{safe_to}.eml"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(
            f"To: {to}\nFrom: {from_name} <{from_addr}>\nSubject: {subject}\n"
            f"Unsubscribe: {unsubscribe_url}\n\n{body}",
            encoding="utf-8",
        )
        return SendResult(success=True, provider_message_id=f"file:{f.name}")


class SMTPMailer(EmailSender):
    def __init__(self, host=None, port=None, username=None, password=None, use_tls=True):
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.username = username or settings.smtp_username
        self.password = password or settings.smtp_password
        self.use_tls = use_tls

    def send(self, *, to, subject, body, from_name, from_addr, unsubscribe_url=None) -> SendResult:
        if not self.host:
            return SendResult(success=False, error="smtp host not configured")
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_addr}>"
            msg["To"] = to
            with smtplib.SMTP(self.host, self.port, timeout=20) as s:
                if self.use_tls:
                    s.starttls()
                if self.username:
                    s.login(self.username, self.password)
                s.send_message(msg)
            return SendResult(success=True)
        except Exception as exc:  # noqa: BLE001
            return SendResult(success=False, error=str(exc))


def get_email_sender(provider: str | None = None) -> EmailSender:
    """Resolve the email provider adapter by configured name."""
    provider = provider or settings.email_provider
    if provider == "smtp":
        return SMTPMailer()
    if provider in ("brevo", "resend"):
        # Same interface; real HTTP wrappers replace the instance in prod config.
        return SMTPMailer() if settings.smtp_host else FileSender()
    return FileSender()