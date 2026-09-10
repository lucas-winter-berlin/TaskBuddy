"""Kurzlebiger Zustand pro User (Drafts, Pending, ListViews)."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Any, Literal, MutableMapping

_token_counter = count(1)
MAX_ENTRIES = 40


def new_token() -> str:
    value = next(_token_counter)
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while value:
        value, rest = divmod(value, 36)
        out = digits[rest] + out
    return out or "0"


@dataclass
class Draft:
    """Aufgabe/Notiz, die gerade erfasst wird."""

    item_type: str  # task | note
    title: str
    body: str | None = None
    project_id: int | None = None
    priority: str | None = None
    project_confidence: float = 0.0
    priority_confidence: float = 0.0
    awaiting: Literal["project", "priority", "new_project", "confirm"] = "project"


@dataclass
class ListView:
    kind: Literal["tasks", "notes", "search"]
    project_id: int | None = None
    argument: str = ""
    offset: int = 0
    title: str = ""


@dataclass
class Pending:
    kind: Literal["new_project"]
    ref: str


def _bucket(user_data: MutableMapping[str, Any], name: str) -> dict[str, Any]:
    bucket = user_data.get(name)
    if not isinstance(bucket, dict):
        bucket = {}
        user_data[name] = bucket
    return bucket


def _store(user_data: MutableMapping[str, Any], name: str, value: Any) -> str:
    bucket = _bucket(user_data, name)
    token = new_token()
    bucket[token] = value
    while len(bucket) > MAX_ENTRIES:
        bucket.pop(next(iter(bucket)))
    return token


def put_draft(user_data: MutableMapping[str, Any], draft: Draft) -> str:
    return _store(user_data, "drafts", draft)


def get_draft(user_data: MutableMapping[str, Any], token: str) -> Draft | None:
    value = _bucket(user_data, "drafts").get(token)
    return value if isinstance(value, Draft) else None


def drop_draft(user_data: MutableMapping[str, Any], token: str) -> None:
    _bucket(user_data, "drafts").pop(token, None)


def put_view(user_data: MutableMapping[str, Any], view: ListView) -> str:
    return _store(user_data, "views", view)


def get_view(user_data: MutableMapping[str, Any], token: str) -> ListView | None:
    value = _bucket(user_data, "views").get(token)
    return value if isinstance(value, ListView) else None


def set_pending(user_data: MutableMapping[str, Any], pending: Pending | None) -> None:
    if pending is None:
        user_data.pop("pending", None)
    else:
        user_data["pending"] = pending


def get_pending(user_data: MutableMapping[str, Any]) -> Pending | None:
    value = user_data.get("pending")
    return value if isinstance(value, Pending) else None
