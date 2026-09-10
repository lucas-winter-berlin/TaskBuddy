"""Inline-Tastaturen und callback_data-Schema."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .. import icons as ic
from ..db.models import Project
from ..services.priority import LABELS, PRIORITIES

CAP = "cap"
ITEM = "item"
PAGE = "pg"
NOOP = "noop"


def _btn(text: str, *, icon: str | None = None, **kwargs) -> InlineKeyboardButton:
    emoji_id = ic.button_icon_id(icon) if icon else None
    if emoji_id:
        return InlineKeyboardButton(text, icon_custom_emoji_id=emoji_id, **kwargs)
    prefix = f"{ic.plain(icon)} " if icon else ""
    return InlineKeyboardButton(f"{prefix}{text}", **kwargs)


def project_picker(token: str, projects: list[Project]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for project in projects:
        row.append(
            InlineKeyboardButton(
                project.name,
                callback_data=f"{CAP}:proj:{token}:{project.id}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [
            _btn("Neues Projekt", icon="edit", callback_data=f"{CAP}:newproj:{token}"),
            _btn("Abbrechen", icon="no", callback_data=f"{CAP}:cancel:{token}"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def priority_picker(token: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{p} · {LABELS[p]}",
                callback_data=f"{CAP}:prio:{token}:{p}",
            )
        ]
        for p in PRIORITIES
    ]
    rows.append([_btn("Abbrechen", icon="no", callback_data=f"{CAP}:cancel:{token}")])
    return InlineKeyboardMarkup(rows)


def confirm_draft(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                _btn("Speichern", icon="ok", callback_data=f"{CAP}:save:{token}"),
                _btn("Projekt", icon="section", callback_data=f"{CAP}:reproj:{token}"),
            ],
            [
                _btn("Priorität", icon="stats", callback_data=f"{CAP}:reprio:{token}"),
                _btn("Abbrechen", icon="no", callback_data=f"{CAP}:cancel:{token}"),
            ],
        ]
    )


def confirm_note(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                _btn("Speichern", icon="ok", callback_data=f"{CAP}:save:{token}"),
                _btn("Projekt", icon="section", callback_data=f"{CAP}:reproj:{token}"),
            ],
            [_btn("Abbrechen", icon="no", callback_data=f"{CAP}:cancel:{token}")],
        ]
    )


def item_actions(item_id: int, *, is_task: bool) -> InlineKeyboardMarkup:
    row = []
    if is_task:
        row.append(_btn("Erledigt", icon="ok", callback_data=f"{ITEM}:done:{item_id}"))
    row.append(_btn("Löschen", icon="trash", callback_data=f"{ITEM}:del:{item_id}"))
    return InlineKeyboardMarkup([row])


def pagination(
    token: str, *, offset: int, has_prev: bool, has_next: bool
) -> InlineKeyboardMarkup | None:
    if not has_prev and not has_next:
        return None
    row: list[InlineKeyboardButton] = []
    if has_prev:
        row.append(_btn("Zurück", icon="refresh", callback_data=f"{PAGE}:{token}:prev"))
    if has_next:
        row.append(_btn("Weiter", icon="save", callback_data=f"{PAGE}:{token}:next"))
    return InlineKeyboardMarkup([row])
