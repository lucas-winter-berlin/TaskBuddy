"""Start, help, settings, fallback, errors."""

from __future__ import annotations

import logging

from telegram import Update

from .. import copy as txt
from .. import keyboards as kb
from ..context import BotContextTypes, app_context, is_authorised, reply, user_id_of

logger = logging.getLogger(__name__)


async def start(update: Update, context: BotContextTypes) -> None:
    settings = app_context(context).settings
    user = update.effective_user
    uid = user.id if user else "?"
    if not is_authorised(update, settings):
        await reply(update, txt.private_with_id(uid))
        return

    ctx = app_context(context)
    async with ctx.db.session() as session:
        await ctx.repository(session).ensure_default_projects(user_id_of(update))

    payload = (context.args or [None])[0] or ""
    if payload.startswith("claim_"):
        from . import share

        await share.handle_claim(update, context, payload)
        return

    await reply(update, txt.START, reply_markup=kb.main_reply_keyboard())


async def menu_command(update: Update, context: BotContextTypes) -> None:
    await reply(update, txt.MENU_READY, reply_markup=kb.main_reply_keyboard())


async def help_command(update: Update, context: BotContextTypes) -> None:
    await reply(update, txt.HELP, reply_markup=kb.main_reply_keyboard())


async def settings_command(update: Update, context: BotContextTypes) -> None:
    s = app_context(context).settings
    backend = "PostgreSQL" if "postgresql" in s.database_url else "SQLite"
    await reply(
        update,
        txt.settings_text(
            owner=str(s.owner_user_id or "offen"),
            backend=backend,
            timezone=str(s.timezone),
            gemini=s.gemini_enabled,
            environment=s.environment,
        ),
        reply_markup=kb.main_reply_keyboard(),
    )


async def task_command(update: Update, context: BotContextTypes) -> None:
    from . import capture

    args = context.args or []
    text = " ".join(args).strip()
    if not text:
        message = update.effective_message
        text = (message.text or "").partition(" ")[2].strip() if message else ""
    if not text:
        await reply(update, txt.TASK_HINT)
        return
    await capture.begin_capture(update, context, text)


async def fallback(update: Update, context: BotContextTypes) -> None:
    if not is_authorised(update, app_context(context).settings):
        return
    await reply(update, txt.FALLBACK, reply_markup=kb.main_reply_keyboard())


async def error_handler(update: object, context: BotContextTypes) -> None:
    logger.exception("Unhandled error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(txt.ERROR, parse_mode="HTML")
        except Exception:
            logger.exception("Failed to send error reply")
