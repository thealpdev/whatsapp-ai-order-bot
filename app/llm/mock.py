"""Rule-based provider used when no API key is set, and in every test.

It speaks the exact same protocol as the real providers (it returns `Turn`s with
tool calls), so the agent loop and the tools are exercised for real — only the
"thinking" is faked. Never touches the network.
"""

from __future__ import annotations

import json
import re

from app.db import StoredMessage
from app.llm.base import ToolCall, ToolSpec, Turn
from app.menu import load_menu, normalize

MENU_KEYWORDS = ("menu", "fiyat", "ne var", "neler var", "kac para", "kacpara", "liste")
NUMBER_WORDS = {
    "bir": 1,
    "iki": 2,
    "uc": 3,
    "dort": 4,
    "bes": 5,
    "alti": 6,
    "yedi": 7,
    "sekiz": 8,
    "dokuz": 9,
    "on": 10,
}


def _aliases(item: dict) -> list[str]:
    name = normalize(item["name"])
    parts = name.split()
    out = {name}
    if len(parts) > 1:
        out.add(parts[0])  # "kiymali" also matches "Kıymalı Pide"
    return sorted(out, key=len, reverse=True)


def _parse_qty(raw: str | None) -> int:
    if not raw:
        return 1
    if raw.isdigit():
        return max(1, int(raw))
    return NUMBER_WORDS.get(raw, 1)


def _collect_items(user_texts: list[str]) -> list[dict]:
    """Merge every menu item mentioned across the conversation window."""
    found: dict[str, dict] = {}
    for text in user_texts:
        norm = normalize(text)
        for item in load_menu()["items"]:
            for alias in _aliases(item):
                pattern = (
                    rf"(?:(\d+|{'|'.join(NUMBER_WORDS)})\s*(?:adet\s*)?)?\b{re.escape(alias)}\b"
                )
                match = re.search(pattern, norm)
                if match:
                    found[item["id"]] = {"name": item["name"], "qty": _parse_qty(match.group(1))}
                    break
    return list(found.values())


def _find_address(window: list[StoredMessage]) -> str:
    # Explicit "adres: ..." anywhere in the window.
    for msg in window:
        if msg.role == "user" and "adres" in normalize(msg.content):
            _, _, tail = msg.content.partition(":")
            if tail.strip():
                return tail.strip()
    # Otherwise: the first thing the customer said after the bot asked for one.
    asked_at = None
    for i, msg in enumerate(window):
        if msg.role == "assistant" and "adres" in normalize(msg.content):
            asked_at = i
    if asked_at is None:
        return ""
    for msg in window[asked_at + 1 :]:
        if msg.role == "user":
            return msg.content.strip()
    return ""


def _window(history: list[StoredMessage]) -> list[StoredMessage]:
    """Only the messages since the last successfully placed order."""
    for i in range(len(history) - 1, -1, -1):
        msg = history[i]
        if msg.role == "tool_result" and msg.tool_name == "create_order":
            try:
                if json.loads(msg.content).get("ok"):
                    return history[i + 1 :]
            except json.JSONDecodeError:
                pass
    return history


def _phone_from_system(system: str) -> str:
    match = re.search(r"telefon numaras[ıi]:\s*(\S+)", system, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _format_menu(menu: dict) -> str:
    lines = [f"- {i['name']} — {i['price']} {menu['currency']}" for i in menu["items"]]
    return "Menümüz şöyle:\n" + "\n".join(lines) + "\nNe alırsın?"


def _summarize(items: list[dict]) -> str:
    return ", ".join(f"{i['qty']} {i['name'].lower()}" for i in items)


class MockProvider:
    """Deterministic stand-in for a real LLM."""

    name = "mock"

    def generate(self, system: str, history: list[StoredMessage], tools: list[ToolSpec]) -> Turn:
        if history and history[-1].role == "tool_result":
            return self._speak_tool_result(history[-1])

        window = _window(history)
        user_texts = [m.content for m in window if m.role == "user"]
        last_user = user_texts[-1] if user_texts else ""

        if any(k in normalize(last_user) for k in MENU_KEYWORDS):
            return Turn(tool_calls=[ToolCall("get_menu", {})])

        items = _collect_items(user_texts)
        if not items:
            return Turn(text="Merhaba, Demo Pide'ye hoş geldin! Menüyü göndereyim mi?")

        address = _find_address(window)
        if not address:
            return Turn(text=f"Sepetin: {_summarize(items)}. Teslimat adresini yazar mısın?")

        return Turn(
            tool_calls=[
                ToolCall(
                    "create_order",
                    {
                        "items": items,
                        "address": address,
                        "phone": _phone_from_system(system),
                    },
                )
            ]
        )

    def _speak_tool_result(self, msg: StoredMessage) -> Turn:
        data = json.loads(msg.content)
        if msg.tool_name == "get_menu":
            return Turn(text=_format_menu(data))
        if msg.tool_name == "create_order":
            if data.get("ok"):
                order = data["order"]
                return Turn(
                    text=(
                        f"Siparişin alındı! Sipariş no #{order['id']}, "
                        f"toplam {order['total']:.0f} TL. 30-40 dk içinde kapında."
                    )
                )
            return Turn(text=f"Siparişi alamadım: {data.get('error')}")
        return Turn(text="Tamamdır.")
