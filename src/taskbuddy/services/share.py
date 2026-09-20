"""Claim-Tokens und Telegram-Share-Links fuer geteilte Aufgaben."""

from __future__ import annotations

import hashlib
import hmac
import re
from urllib.parse import quote

_CLAIM_RE = re.compile(r"^claim_(\d+)_([0-9a-f]{10})$")
_SIG_LEN = 10
_SHARE_TEXT_LIMIT = 400
_SHARE_URL_LIMIT = 2048


def claim_payload(item_id: int, secret: str) -> str:
    sig = hmac.new(
        secret.encode("utf-8"),
        str(item_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:_SIG_LEN]
    return f"claim_{item_id}_{sig}"


def parse_claim_payload(payload: str, secret: str) -> int | None:
    match = _CLAIM_RE.match((payload or "").strip())
    if match is None:
        return None
    item_id = int(match.group(1))
    expected = claim_payload(item_id, secret)
    if not hmac.compare_digest(expected, payload.strip()):
        return None
    return item_id


def claim_url(bot_username: str, payload: str) -> str:
    return f"https://t.me/{bot_username.lstrip('@')}?start={payload}"


def telegram_share_url(*, url: str, text: str) -> str:
    """Oeffnet Telegrams eigenen Chat-Picker mit fertigem Aufgabentext."""
    clipped = (text or "").strip()[:_SHARE_TEXT_LIMIT]
    while True:
        result = (
            "https://t.me/share/url"
            f"?url={quote(url, safe='')}"
            f"&text={quote(clipped, safe='')}"
        )
        if len(result) <= _SHARE_URL_LIMIT or len(clipped) < 20:
            return result
        clipped = clipped[: max(0, len(clipped) - 80)].rstrip() + "…"
