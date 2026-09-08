"""Minimal WhatsApp Cloud API client + webhook helpers."""

from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


def verify_signature(body: bytes, header: str | None, app_secret: str | None) -> bool:
    """Validate Meta's X-Hub-Signature-256 header. Skipped when no secret is set."""
    if not app_secret:
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def extract_text_messages(payload: dict) -> list[tuple[str, str]]:
    """Pull (from_phone, text) pairs out of a webhook payload. Ignores everything else."""
    out: list[tuple[str, str]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") == "text":
                    out.append((message["from"], message["text"]["body"]))
    return out


def send_text(settings: Settings, to: str, body: str) -> None:
    if not (settings.wa_access_token and settings.wa_phone_number_id):
        logger.warning("WhatsApp credentials missing; reply to %s not sent: %s", to, body)
        return
    url = (
        f"https://graph.facebook.com/{settings.wa_api_version}"
        f"/{settings.wa_phone_number_id}/messages"
    )
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.wa_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            },
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Failed to send WhatsApp message to %s", to)
