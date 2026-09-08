"""Application settings, read from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # storage
    db_path: str = str(PROJECT_DIR / "data" / "bot.db")
    menu_path: str = str(PACKAGE_DIR / "menu.json")

    # llm
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    history_limit: int = 20

    # whatsapp cloud api
    wa_verify_token: str = "change-me"
    wa_access_token: str | None = None
    wa_phone_number_id: str | None = None
    wa_app_secret: str | None = None
    wa_api_version: str = "v21.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
