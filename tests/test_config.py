"""Config-Smoke-Tests."""

from __future__ import annotations

from pathlib import Path

from taskbuddy.config import load_settings


def test_load_settings_sqlite_default(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=1:test\nOWNER_USER_ID=42\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = load_settings(env)
    assert settings.owner_user_id == 42
    assert "taskbuddy.db" in settings.database_url or "sqlite" in settings.database_url
