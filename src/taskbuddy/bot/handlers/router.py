"""Free-text router: menu buttons, pending input, or new capture."""

from __future__ import annotations

from telegram import Update

from ...services.intent import parse_text_intent
from .. import copy as txt
from .. import keyboards as kb
from .. import state
from ..context import BotContextTypes, app_context, is_authorised, respond
from . import capture, manage, query


async def text_router(update: Update, context: BotContextTypes) -> None:
    settings = app_context(context).settings
    if not is_authorised(update, settings):
        await respond(update, txt.PRIVATE_LOCK)
        return

    message = update.effective_message
    if message is None:
        return
    text = (message.text or message.caption or "").strip()
    if not text:
        return

    if await _dispatch_menu_button(update, context, text):
        state.set_pending(context.user_data, None)
        return

    pending = state.get_pending(context.user_data)
    if pending and pending.kind == "menu_search":
        state.set_pending(context.user_data, None)
        await query.search_with_keyword(update, context, text)
        return
    if pending and pending.kind in {"edit_title", "edit_notes", "edit_subtask"}:
        if await manage.apply_pending_edit(update, context, pending, text):
            return

    intent = parse_text_intent(text)
    if intent is not None:
        handlers = {
            "done": manage.handle_done_query,
            "undo": manage.handle_undo_query,
            "edit": manage.handle_edit_query,
        }
        await handlers[intent.kind](update, context, intent.query)
        return

    await capture.begin_capture(update, context, text)


def _normalize_menu_label(text: str) -> str:
    cleaned = (
        text.strip()
        .replace("\ufe0f", "")
        .replace("\u200d", "")
        .replace("\u00a0", " ")
    )
    return " ".join(cleaned.split())


def _menu_action_key(text: str) -> str | None:
    label = _normalize_menu_label(text)
    candidates = {
        _normalize_menu_label(kb.BTN_TASKS): "tasks",
        _normalize_menu_label(kb.BTN_BACKLOG): "backlog",
        _normalize_menu_label(kb.BTN_SEARCH): "search",
    }
    if label in candidates:
        return candidates[label]
    word = label.split(" ")[-1].lower() if label else ""
    return {
        "tasks": "tasks",
        "aufgaben": "tasks",
        "backlog": "backlog",
        "search": "search",
        "suchen": "search",
    }.get(word)


async def _dispatch_menu_button(
    update: Update, context: BotContextTypes, text: str
) -> bool:
    action = _menu_action_key(text)
    if action is None:
        return False
    if action == "tasks":
        await query.tasks_command(update, context, args=[])
        return True
    if action == "backlog":
        await query.backlog_command(update, context, args=[])
        return True
    if action == "search":
        state.set_pending(
            context.user_data, state.Pending(kind="menu_search", ref="")
        )
        await respond(update, txt.SEARCH_PROMPT)
        return True
    return False
