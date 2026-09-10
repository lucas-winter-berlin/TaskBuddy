"""UI icons: Telegram custom emoji with Unicode fallback."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PACK_PATH = Path(__file__).resolve().parents[2] / "assets" / "emoji_pack.json"

_TEXT = {
    "ok": "✓",
    "no": "×",
    "edit": "›",
    "note": "≡",
    "link": "›",
    "search": "▸",
    "stats": "▸",
    "related": "▸",
    "save": "›",
    "refresh": "↺",
    "trash": "×",
    "warn": "!",
    "wait": "…",
    "section": "▸",
    "export": "›",
    "tag": "#",
    "gear": "▸",
    "lock": "▸",
    "tip": "·",
}

_EMOJI_FALLBACK = {
    "ok": "✅",
    "no": "❌",
    "edit": "✏️",
    "note": "📝",
    "link": "🔗",
    "search": "🔍",
    "stats": "📊",
    "related": "🔀",
    "save": "💾",
    "refresh": "🔄",
    "trash": "🗑",
    "warn": "⚠️",
    "wait": "⏳",
    "section": "▪",
    "export": "📤",
    "tag": "🏷",
    "gear": "⚙️",
    "lock": "🔒",
    "tip": "💡",
}

_ALIASES = {
    "OK": "ok",
    "CHECK": "ok",
    "NO": "no",
    "EDIT": "edit",
    "NOTE": "note",
    "LINK": "link",
    "TAG": "tag",
    "SEARCH": "search",
    "STATS": "stats",
    "CHART": "stats",
    "RELATED": "related",
    "SAVE": "save",
    "REFRESH": "refresh",
    "TRASH": "trash",
    "WARN": "warn",
    "WAIT": "wait",
    "SECTION": "section",
    "BOOK": "section",
    "INFO": "tip",
    "GEAR": "gear",
    "LOCK": "lock",
    "MAIL": "export",
    "NEW": "ok",
    "EXPORT": "export",
    "TIP": "tip",
    "EMPTY": "tip",
    "NAV_PREV": "refresh",
    "NAV_NEXT": "save",
    "TREND_UP": "stats",
    "TREND_DOWN": "stats",
    "TIME": "wait",
    "DATE": "wait",
}

DIVIDER = "─" * 24


@lru_cache(maxsize=1)
def _pack() -> dict:
    if not _PACK_PATH.exists():
        return {}
    try:
        return json.loads(_PACK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def reload_pack() -> None:
    _pack.cache_clear()


def has_custom_emoji() -> bool:
    return bool(_pack().get("ids"))


def emoji_id(name: str) -> str | None:
    ids = _pack().get("ids") or {}
    value = ids.get(name)
    return str(value) if value else None


def fallback_emoji(name: str) -> str:
    pack_fb = (_pack().get("fallbacks") or {}).get(name)
    return pack_fb or _EMOJI_FALLBACK.get(name) or _TEXT.get(name, "·")


def html(name: str) -> str:
    eid = emoji_id(name)
    fb = fallback_emoji(name)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
    return fb


def plain(name: str) -> str:
    return fallback_emoji(name)


def button_icon_id(name: str) -> str | None:
    return emoji_id(name)


def mark(index: int) -> str:
    return f"{index:02d}"


def __getattr__(name: str) -> str:
    key = _ALIASES.get(name)
    if key is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return html(key)
