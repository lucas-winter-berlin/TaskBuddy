"""Inline keyboards, reply keyboard, and callback_data schema."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from .. import icons as ic
from ..db.models import Item, Project
from ..services.priority import LABELS, PRIORITIES
from . import copy as txt

CAP = "cap"
ITEM = "item"
PAGE = "pg"
CLR = "clr"
EDT = "edt"
NOOP = "noop"

BTN_TASKS = txt.KEYBOARD_TASKS
BTN_BACKLOG = txt.KEYBOARD_BACKLOG
BTN_SEARCH = txt.KEYBOARD_SEARCH


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(BTN_TASKS),
                KeyboardButton(BTN_BACKLOG),
                KeyboardButton(BTN_SEARCH),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=txt.KEYBOARD_PLACEHOLDER,
    )


def _btn(text: str, *, icon: str | None = None, **kwargs) -> InlineKeyboardButton:
    emoji_id = ic.button_icon_id(icon) if icon else None
    if emoji_id:
        return InlineKeyboardButton(text, icon_custom_emoji_id=emoji_id, **kwargs)
    prefix = f"{ic.plain(icon)} " if icon else ""
    return InlineKeyboardButton(f"{prefix}{text}", **kwargs)


def _chunk(items: Sequence, size: int) -> list[list]:
    rows: list[list] = []
    row: list = []
    for item in items:
        row.append(item)
        if len(row) == size:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def _cancel(data: str) -> list[InlineKeyboardButton]:
    return [_btn(txt.BTN_CANCEL, icon="no", callback_data=data)]


def _back(item_id: int) -> list[InlineKeyboardButton]:
    return [_btn(txt.BTN_BACK, icon="refresh", callback_data=f"{EDT}:show:{item_id}")]


def _project_grid(
    projects: Iterable[Project],
    data_for: Callable[[Project], str],
) -> list[list[InlineKeyboardButton]]:
    buttons = [
        InlineKeyboardButton(project.name, callback_data=data_for(project))
        for project in projects
    ]
    return _chunk(buttons, 2)


def _priority_rows(data_for: Callable[[str], str]) -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton(f"{p} · {LABELS[p]}", callback_data=data_for(p))]
        for p in PRIORITIES
    ]


def _short_label(title: str, limit: int = 28) -> str:
    cleaned = " ".join((title or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def project_picker(token: str, projects: list[Project]) -> InlineKeyboardMarkup:
    rows = _project_grid(projects, lambda p: f"{CAP}:proj:{token}:{p.id}")
    rows.append(_cancel(f"{CAP}:cancel:{token}"))
    return InlineKeyboardMarkup(rows)


def priority_picker(token: str) -> InlineKeyboardMarkup:
    rows = _priority_rows(lambda p: f"{CAP}:prio:{token}:{p}")
    rows.append(_cancel(f"{CAP}:cancel:{token}"))
    return InlineKeyboardMarkup(rows)


def confirm_draft(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                _btn(txt.BTN_SAVE, icon="ok", callback_data=f"{CAP}:save:{token}"),
                _btn(txt.BTN_PROJECT, icon="section", callback_data=f"{CAP}:reproj:{token}"),
            ],
            [
                _btn(txt.BTN_PRIORITY, icon="stats", callback_data=f"{CAP}:reprio:{token}"),
                _btn(txt.BTN_CANCEL, icon="no", callback_data=f"{CAP}:cancel:{token}"),
            ],
        ]
    )


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
    for key, label in (("all", txt.BTN_ALL), *[(p, p) for p in PRIORITIES]):
        current = (priority is None and key == "all") or priority == key
        text = f"· {label} ·" if current else label
        filters.append(InlineKeyboardButton(text, callback_data=f"{PAGE}:{token}:{key}"))
    rows.append(filters)

    if priority is not None:
        done_buttons = [
            _btn(f"#{item.number}", icon="ok", callback_data=f"{ITEM}:done:{item.id}:{token}")
            for item in items
        ]
        rows.extend(_chunk(done_buttons, 3))

    if items:
        rows.append(
            [_btn(txt.BTN_CLEAR, icon="trash", callback_data=f"{CLR}:ask:{token}")]
        )

    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(_btn(txt.BTN_BACK, icon="refresh", callback_data=f"{PAGE}:{token}:prev"))
    if has_next:
        nav.append(_btn(txt.BTN_NEXT, icon="export", callback_data=f"{PAGE}:{token}:next"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def confirm_clear_all(_count: int, token: str | None = None) -> InlineKeyboardMarkup:
    suffix = f":{token}" if token else ""
    return InlineKeyboardMarkup(
        [
            [
                _btn(txt.BTN_DELETE, icon="trash", callback_data=f"{CLR}:yes{suffix}"),
                _btn(txt.BTN_CANCEL, icon="no", callback_data=f"{CLR}:no{suffix}"),
            ]
        ]
    )


def match_picker(kind: str, items: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in items[:8]:
        data = f"{EDT}:show:{item.id}" if kind == "edit" else f"{ITEM}:done:{item.id}"
        rows.append(
            [
                InlineKeyboardButton(
                    f"#{item.number} {_short_label(item.title)}",
                    callback_data=data,
                )
            ]
        )
    rows.append(_cancel(f"{EDT}:noop:0"))
    return InlineKeyboardMarkup(rows)


def restore_list_keyboard(items: list) -> InlineKeyboardMarkup:
    buttons = [
        _btn(f"#{item.number}", icon="refresh", callback_data=f"{ITEM}:undo:{item.id}")
        for item in items[:12]
    ]
    return InlineKeyboardMarkup(_chunk(buttons, 3))


def subtask_match_picker(subtasks: list) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                _short_label(sub.title),
                callback_data=f"{EDT}:tog:{sub.item_id}:{sub.id}",
            )
        ]
        for sub in subtasks[:8]
    ]
    rows.append(_cancel(f"{EDT}:noop:0"))
    return InlineKeyboardMarkup(rows)


def edit_task_keyboard(
    item_id: int,
    subtasks: list,
    *,
    number: int | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            _btn(txt.BTN_TITLE, icon="edit", callback_data=f"{EDT}:title:{item_id}"),
            _btn(txt.BTN_NOTES, icon="note", callback_data=f"{EDT}:notes:{item_id}"),
        ],
        [
            _btn(txt.BTN_PRIORITY, icon="stats", callback_data=f"{EDT}:prio:{item_id}"),
            _btn(txt.BTN_PROJECT, icon="section", callback_data=f"{EDT}:proj:{item_id}"),
        ],
    ]
    checklist = []
    for sub in subtasks[:8]:
        mark = "✓" if getattr(sub, "done_at", None) else "·"
        checklist.append(
            InlineKeyboardButton(
                f"{mark}  {_short_label(sub.title, 18)}",
                callback_data=f"{EDT}:tog:{item_id}:{sub.id}",
            )
        )
    rows.extend(_chunk(checklist, 2))
    rows.append(
        [_btn(txt.BTN_SUBTASK, icon="save", callback_data=f"{EDT}:add:{item_id}")]
    )
    share_query = f"#{number}" if number is not None else ""
    rows.append(
        [
            _btn(txt.BTN_DONE, icon="ok", callback_data=f"{ITEM}:done:{item_id}"),
            _btn(txt.BTN_SHARE, icon="link", switch_inline_query=share_query),
        ]
    )
    rows.append(
        [
            _btn(txt.BTN_DELETE, icon="trash", callback_data=f"{ITEM}:del:{item_id}"),
            _btn(txt.BTN_CLOSE, icon="no", callback_data=f"{EDT}:close:{item_id}"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def claim_keyboard(bot_username: str, payload: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/{bot_username}?start={payload}"
    return InlineKeyboardMarkup(
        [[_btn(txt.BTN_CLAIM, icon="save", url=url)]]
    )


def edit_priority_picker(item_id: int) -> InlineKeyboardMarkup:
    rows = _priority_rows(lambda p: f"{EDT}:setr:{item_id}:{p}")
    rows.append(_back(item_id))
    return InlineKeyboardMarkup(rows)


def edit_project_picker(item_id: int, projects: list[Project]) -> InlineKeyboardMarkup:
    rows = _project_grid(projects, lambda p: f"{EDT}:setp:{item_id}:{p.id}")
    rows.append(_back(item_id))
    return InlineKeyboardMarkup(rows)
