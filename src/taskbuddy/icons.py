"""UI icons: Telegram custom emoji with Unicode fallback."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PACK_PATH = Path(__file__).resolve().parents[2] / "assets" / "emoji_pack.json"

# Einfarbige Textzeichen. Telegram färbt Custom-Emoji mit needs_repainting.
_TEXT = {
    "ok": "✓",
    "no": "×",
    "edit": "✎",
    "note": "≡",
    "link": "↗",
    "search": "⌕",
    "stats": "▤",
    "related": "⚭",
    "save": "↓",
    "refresh": "↺",
    "trash": "⌫",
    "warn": "!",
    "wait": "…",
    "section": "·",
    "export": "↑",
    "tag": "#",
    "gear": "⚙",
    "lock": "⊘",
    "tip": "·",
}


@lru_cache(maxsize=1)
def _pack() -> dict:
    if not _PACK_PATH.exists():
        return {}
    try:
        return json.loads(_PACK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def emoji_id(name: str) -> str | None:
    ids = _pack().get("ids") or {}
    value = ids.get(name)
    return str(value) if value else None


def fallback_emoji(name: str) -> str:
    pack_fb = (_pack().get("fallbacks") or {}).get(name)
    return pack_fb or _TEXT.get(name, "·")


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
