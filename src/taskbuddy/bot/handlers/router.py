"""Freitext-Router."""

from __future__ import annotations

from telegram import Update

from ... import icons as ic
from .. import state
from ..context import BotContextTypes, app_context, is_authorised, reply
from . import capture


async def text_router(update: Update, context: BotContextTypes) -> None:
    settings = app_context(context).settings
    if not is_authorised(update, settings):
        await reply(update, f"{ic.html('lock')} Dieser Bot ist privat.")
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

    await capture.begin_capture(update, context, text, default_type="task")
