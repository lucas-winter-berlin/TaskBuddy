"""Inline keyboards, reply keyboard, and callback_data schema."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from .. import icons as ic
from ..db.models import Item, Project
from ..services.priority import LABELS, PRIORITIES

CAP = "cap"
ITEM = "item"
PAGE = "pg"
CLR = "clr"
NOOP = "noop"

BTN_TASKS = "✅ Tasks"
BTN_BACKLOG = "📦 Backlog"
BTN_SEARCH = "🔍 Search"
BTN_HELP = "❓ Help"
BTN_SETTINGS = "⚙️ Settings"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(BTN_TASKS),
                KeyboardButton(BTN_BACKLOG),
                KeyboardButton(BTN_SEARCH),
            ],
            [
                KeyboardButton(BTN_HELP),
                KeyboardButton(BTN_SETTINGS),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Type a task or tap a button…",
    )


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
    rows.append([_btn("Cancel", icon="no", callback_data=f"{CAP}:cancel:{token}")])
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
    rows.append([_btn("Cancel", icon="no", callback_data=f"{CAP}:cancel:{token}")])
    return InlineKeyboardMarkup(rows)


def confirm_draft(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                _btn("Save", icon="ok", callback_data=f"{CAP}:save:{token}"),
                _btn("Project", icon="section", callback_data=f"{CAP}:reproj:{token}"),
            ],
            [
                _btn("Priority", icon="stats", callback_data=f"{CAP}:reprio:{token}"),
                _btn("Cancel", icon="no", callback_data=f"{CAP}:cancel:{token}"),
            ],
        ]
    )


def item_actions(item_id: int, *, is_task: bool = True) -> InlineKeyboardMarkup:
    row = []
    if is_task:
        row.append(_btn("Done", icon="ok", callback_data=f"{ITEM}:done:{item_id}"))
    row.append(_btn("Delete", icon="trash", callback_data=f"{ITEM}:del:{item_id}"))
    return InlineKeyboardMarkup([row])


def task_list_keyboard(
    token: str,
    items: list[Item],
    *,
    has_prev: bool,
    has_next: bool,
    priority: str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    filters: list[InlineKeyboardButton] = []
    for key, label in (("all", "All"), *[(p, p) for p in PRIORITIES]):
        current = (priority is None and key == "all") or priority == key
        text = f"· {label} ·" if current else label
        filters.append(InlineKeyboardButton(text, callback_data=f"{PAGE}:{token}:{key}"))
    rows.append(filters)

    if priority is not None:
        done_row: list[InlineKeyboardButton] = []
        for item in items:
            done_row.append(
                _btn(
                    f"Done #{item.id}",
                    icon="ok",
                    callback_data=f"{ITEM}:done:{item.id}:{token}",
                )
            )
            if len(done_row) == 3:
                rows.append(done_row)
                done_row = []
        if done_row:
            rows.append(done_row)

    if items:
        rows.append(
            [_btn("Clear all", icon="trash", callback_data=f"{CLR}:ask:{token}")]
        )

    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(_btn("Back", icon="refresh", callback_data=f"{PAGE}:{token}:prev"))
    if has_next:
        nav.append(_btn("Next", icon="save", callback_data=f"{PAGE}:{token}:next"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def confirm_clear_all(count: int, token: str | None = None) -> InlineKeyboardMarkup:
    suffix = f":{token}" if token else ""
    return InlineKeyboardMarkup(
        [
            [
                _btn(
                    f"Yes, delete all {count}",
                    icon="trash",
                    callback_data=f"{CLR}:yes{suffix}",
                ),
                _btn("Cancel", icon="no", callback_data=f"{CLR}:no{suffix}"),
            ]
        ]
    )
