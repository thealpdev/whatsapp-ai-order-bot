"""Test fixtures. Every test runs against MockProvider and a throwaway SQLite file."""

from __future__ import annotations

import pytest

from app.deps import get_db, reset_caches


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Fresh DB per test, and no way to reach a real LLM."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("WA_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("WA_VERIFY_TOKEN", "test-verify-token")
    reset_caches()
    yield
    reset_caches()


@pytest.fixture
def db():
    return get_db()


@pytest.fixture
def provider():
    from app.llm.factory import get_provider

    p = get_provider()
    assert p.name == "mock", "tests must never hit a real provider"
    return p
