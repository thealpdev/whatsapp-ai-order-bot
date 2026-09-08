"""The conversation loop: history -> provider -> tools -> reply."""

from __future__ import annotations

import json
import logging

from app.config import get_settings
from app.db import Database
from app.llm.base import LLMProvider
from app.prompts import build_system_prompt
from app.tools import TOOL_SPECS, run_tool

logger = logging.getLogger(__name__)

MAX_TOOL_STEPS = 5
FALLBACK = "Kusura bakma, biraz karıştırdım. Ne almak istediğini tekrar yazar mısın?"


def handle_message(phone: str, text: str, db: Database, provider: LLMProvider) -> str:
    """Process one incoming customer message and return the reply text."""
    settings = get_settings()
    system = build_system_prompt(phone)
    db.add_message(phone, "user", text)

    for _ in range(MAX_TOOL_STEPS):
        history = db.get_history(phone, limit=settings.history_limit)
        turn = provider.generate(system, history, TOOL_SPECS)

        if turn.tool_calls:
            for call in turn.tool_calls:
                logger.info("tool call: %s %s", call.name, call.args)
                db.add_message(
                    phone, "tool_call", json.dumps(call.args, ensure_ascii=False), call.name
                )
                result = run_tool(call.name, call.args, db)
                db.add_message(
                    phone, "tool_result", json.dumps(result, ensure_ascii=False), call.name
                )
            continue

        reply = (turn.text or "").strip() or FALLBACK
        db.add_message(phone, "assistant", reply)
        return reply

    db.add_message(phone, "assistant", FALLBACK)
    return FALLBACK
