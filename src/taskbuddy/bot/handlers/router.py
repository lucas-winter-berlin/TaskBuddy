"""Free-text router: menu buttons, pending input, or new capture."""

from __future__ import annotations

from telegram import Update

from ... import icons as ic
from .. import keyboards as kb
from .. import state
from ..context import BotContextTypes, app_context, is_authorised, reply
from . import capture, common, manage, query


async def text_router(update: Update, context: BotContextTypes) -> None:
    settings = app_context(context).settings
    if not is_authorised(update, settings):
        await reply(
            update,
            f"{ic.html('lock')} This bot is private.",
        )
        return

    message = update.effective_message
    if message is None:
        return
    text = (message.text or message.caption or "").strip()
    if not text:
        return

    pending = state.get_pending(context.user_data)
    if pending and pending.kind == "new_project":
        await capture.handle_new_project_name(update, context, pending.ref, text)
        return
    if pending and pending.kind == "menu_search":
        state.set_pending(context.user_data, None)
        await query.search_with_keyword(update, context, text)
        return

    if await _dispatch_menu_button(update, context, text):
        return

    await capture.begin_capture(update, context, text, default_type="task")


async def _dispatch_menu_button(
    update: Update, context: BotContextTypes, text: str
) -> bool:
    label = text.strip()
    if label == kb.BTN_TASKS:
        context.args = []
        await query.tasks_command(update, context)
        return True
    if label == kb.BTN_NOTES:
        context.args = []
        await query.notes_command(update, context)
        return True
    if label == kb.BTN_PROJECTS:
        await manage.projects_command(update, context)
        return True
    if label == kb.BTN_SEARCH:
        state.set_pending(
            context.user_data, state.Pending(kind="menu_search", ref="")
        )
        await reply(
            update,
            f"{ic.html('search')} Send a search keyword "
            f"(or type a new task instead).",
        )
        return True
    if label == kb.BTN_HELP:
        await common.help_command(update, context)
        return True
    if label == kb.BTN_SETTINGS:
        await common.settings_command(update, context)
        return True
    return False
