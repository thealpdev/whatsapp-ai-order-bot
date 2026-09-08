"""Picks the LLM provider: real one if a key is configured, mock otherwise."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.mock import MockProvider


@lru_cache
def get_provider() -> LLMProvider:
    settings = get_settings()
    if settings.gemini_api_key:
        from app.llm.gemini import GeminiProvider  # imported lazily: optional dependency

        return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    return MockProvider()
