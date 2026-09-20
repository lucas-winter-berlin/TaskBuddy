"""Claim-Tokens fuer geteilte Aufgaben (HMAC, kein Extra-Table)."""

from __future__ import annotations

import hmac
import hashlib
import re

_CLAIM_RE = re.compile(r"^claim_(\d+)_([0-9a-f]{10})$")
_SIG_LEN = 10


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
