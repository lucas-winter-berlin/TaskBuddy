"""Freitext-Intents: done/edit und Checklisten-Zeilen."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Sequence

_DONE_PREFIX = re.compile(r"^(?:done|erledigt|fertig)\b[\s:–-]*", re.IGNORECASE)
_EDIT_PREFIX = re.compile(r"^(?:edit|bearbeiten)\b[\s:–-]*", re.IGNORECASE)
_UNDO_PREFIX = re.compile(
    r"^(?:undo|undone|restore|rückgängig|rueckgaengig|wiederherstellen)\b[\s:–-]*",
    re.IGNORECASE,
)
_CHECKED = re.compile(r"^\s*\[(?:x|X)\]\s+(.+\S)\s*$")
_UNCHECKED = re.compile(r"^\s*(?:[-*]|\[ \]|\[\])\s+(.+\S)\s*$")
_ID_QUERY = re.compile(r"^#?(\d+)$")
_HASH_ID = re.compile(r"^#(\d+)$")

MIN_SUBSTRING = 3


@dataclass(frozen=True)
class TextIntent:
    kind: Literal["done", "edit", "undo"]
    query: str


def parse_text_intent(text: str) -> TextIntent | None:
    raw = (text or "").strip()
    if not raw:
        return None
    match = _DONE_PREFIX.match(raw)
    if match:
        return TextIntent("done", raw[match.end() :].strip())
    match = _EDIT_PREFIX.match(raw)
    if match:
        return TextIntent("edit", raw[match.end() :].strip())
    match = _UNDO_PREFIX.match(raw)
    if match:
        return TextIntent("undo", raw[match.end() :].strip())
    if _HASH_ID.fullmatch(raw):
        return TextIntent("edit", raw)
    return None


def parse_item_id(query: str) -> int | None:
    raw = (query or "").strip()
    match = _ID_QUERY.fullmatch(raw)
    if not match:
        return None
    return int(match.group(1))


def match_by_title(items: Sequence, query: str, *, min_len: int = MIN_SUBSTRING) -> list:
    """Exakter Titel gewinnt, sonst eindeutiger/mehrdeutiger Teilstring."""
    needle = (query or "").strip().casefold()
    if not needle:
        return []
    exact = [item for item in items if (item.title or "").casefold() == needle]
    if exact:
        return exact
    if len(needle) < min_len:
        return []
    return [item for item in items if needle in (item.title or "").casefold()]


def split_notes_and_subtasks(body: str | None) -> tuple[str | None, list[tuple[str, bool]]]:
    """Fliesstext vs. Zeilen mit - / * / [ ] / [x]."""
    if not body:
        return None, []
    notes: list[str] = []
    subtasks: list[tuple[str, bool]] = []
    for line in body.splitlines():
        checked = _CHECKED.match(line)
        if checked:
            subtasks.append((checked.group(1).strip(), True))
            continue
        unchecked = _UNCHECKED.match(line)
        if unchecked:
            subtasks.append((unchecked.group(1).strip(), False))
            continue
        notes.append(line)
    note_text = "\n".join(notes).strip() or None
    return note_text, subtasks
