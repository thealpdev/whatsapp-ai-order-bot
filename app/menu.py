"""Menu loading and lookup helpers."""

from __future__ import annotations

import json
from functools import lru_cache

from app.config import get_settings


@lru_cache
def load_menu() -> dict:
    with open(get_settings().menu_path, encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str) -> str:
    """Lowercase + strip Turkish diacritics, so 'Kıymalı' matches 'kiymali'."""
    lowered = text.replace("I", "ı").replace("İ", "i").lower()
    table = str.maketrans("ıçğöşü", "icgosu")
    return lowered.translate(table)


def find_item(name: str) -> dict | None:
    """Match a menu item by id or (diacritic-insensitive) name."""
    wanted = normalize(name).strip()
    for item in load_menu()["items"]:
        if wanted in (item["id"], normalize(item["name"])):
            return item
    return None
