"""FastAPI app: WhatsApp webhook + a tiny orders endpoint."""

from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Request, Response

from app.agent import handle_message
from app.config import get_settings
from app.deps import get_db
from app.llm.factory import get_provider
from app.whatsapp import extract_text_messages, send_text, verify_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp AI Order Bot", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": get_provider().name}


@app.get("/orders")
def list_orders(limit: int = 100) -> dict:
    return {"orders": get_db().list_orders(limit=limit)}


@app.get("/webhook")
def verify_webhook(request: Request) -> Response:
    """Meta calls this once when you register the webhook URL."""
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == get_settings().wa_verify_token
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(content="forbidden", status_code=403, media_type="text/plain")


@app.post("/webhook", response_model=None)
async def receive_webhook(request: Request, background: BackgroundTasks) -> Response | dict:
    settings = get_settings()
    raw = await request.body()

    if not verify_signature(
        raw, request.headers.get("X-Hub-Signature-256"), settings.wa_app_secret
    ):
        return Response(content="invalid signature", status_code=403, media_type="text/plain")

    payload = await request.json()
    for phone, text in extract_text_messages(payload):
        background.add_task(_reply, phone, text)

    # Meta retries anything slower than ~20s, so answer immediately.
    return {"status": "received"}


def _reply(phone: str, text: str) -> None:
    try:
        answer = handle_message(phone, text, get_db(), get_provider())
        send_text(get_settings(), phone, answer)
    except Exception:
        logger.exception("Failed to handle message from %s", phone)
