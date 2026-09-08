"""Singletons, in one place so tests can reset them."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.db import Database


@lru_cache
def get_db() -> Database:
    return Database(get_settings().db_path)


def reset_caches() -> None:
    """Drop every cached singleton (used by the test fixtures)."""
    from app.llm.factory import get_provider
    from app.menu import load_menu

    get_settings.cache_clear()
    get_db.cache_clear()
    get_provider.cache_clear()
    load_menu.cache_clear()
