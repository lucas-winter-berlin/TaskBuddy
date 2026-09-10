"""Zentrale Konfiguration, aus Umgebungsvariablen gelesen."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Wird geworfen, wenn Pflicht-Konfiguration fehlt oder unbrauchbar ist."""


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_url: str
    owner_user_id: int | None
    gemini_api_key: str | None
    gemini_model: str
    timezone: ZoneInfo
    max_title_length: int
    max_body_length: int
    page_size: int
    classify_confidence_threshold: float
    log_level: str
    environment: str

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} muss eine Zahl sein, war: {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} muss eine Zahl sein, war: {raw!r}") from exc


def _normalise_database_url(raw: str) -> str:
    url = raw.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        url = "sqlite+aiosqlite://" + url[len("sqlite://") :]
    return url


def load_settings(env_file: str | os.PathLike[str] | None = None) -> Settings:
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "TELEGRAM_BOT_TOKEN fehlt. Lege eine .env nach dem Vorbild von "
            ".env.example an."
        )

    default_db = f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'taskbuddy.db').as_posix()}"
    database_url = _normalise_database_url(os.getenv("DATABASE_URL", default_db))

    owner_raw = os.getenv("OWNER_USER_ID", "").strip()
    owner_user_id = int(owner_raw) if owner_raw else None

    tz_name = os.getenv("BOT_TIMEZONE", "Europe/Berlin").strip() or "Europe/Berlin"
    try:
        timezone = ZoneInfo(tz_name)
    except Exception as exc:
        raise ConfigError(f"BOT_TIMEZONE unbekannt: {tz_name!r}") from exc

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or None

    return Settings(
        telegram_bot_token=token,
        database_url=database_url,
        owner_user_id=owner_user_id,
        gemini_api_key=gemini_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip(),
        timezone=timezone,
        max_title_length=_env_int("MAX_TITLE_LENGTH", 500),
        max_body_length=_env_int("MAX_BODY_LENGTH", 4000),
        page_size=_env_int("PAGE_SIZE", 10),
        classify_confidence_threshold=_env_float("CLASSIFY_CONFIDENCE", 0.7),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        environment=os.getenv("DEPLOYMENT_ENV", "development").strip(),
    )
