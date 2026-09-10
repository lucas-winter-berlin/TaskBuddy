"""Start, help, settings, fallback, errors."""

from __future__ import annotations

import html
import logging

from telegram import Update

from ... import icons as ic
from .. import keyboards as kb
from ..context import BotContextTypes, app_context, is_authorised, reply, user_id_of

logger = logging.getLogger(__name__)

HELP_TEXT = f"""{ic.html('tip')} <b>TaskBuddy – Commands</b>

Send text → new <b>task</b>
<code>note: …</code> or /note → <b>note</b>

Bottom keyboard – tap Tasks / Notes / Projects / Search

/tasks [project] – tasks (A→D)
/notes [project] – notes
/projects – list projects
/project new Name – create project
/project rename Old -&gt; New
/project delete Name – custom project (+ items)
/done ID – complete task (remove)
/search … – search
/menu – show keyboard again
/settings – config
/help – this help

Priorities:
A Important &amp; Urgent
B Urgent &amp; Not important
C Important &amp; Not urgent
D Not important &amp; Not urgent
"""


async def start(update: Update, context: BotContextTypes) -> None:
    settings = app_context(context).settings
    user = update.effective_user
    uid = user.id if user else "?"
    if not is_authorised(update, settings):
        await reply(
            update,
            f"{ic.html('lock')} This bot is private.\nYour user id: <code>{uid}</code>",
        )
        return

    ctx = app_context(context)
    async with ctx.db.session() as session:
        await ctx.repository(session).ensure_default_projects(user_id_of(update))

    await reply(
        update,
        f"{ic.html('ok')} <b>TaskBuddy</b> ready.\n"
        f"Type a task, or use the buttons below.\n"
        f"/help for all commands · /menu shows the keyboard again.",
        reply_markup=kb.main_reply_keyboard(),
    )


async def menu_command(update: Update, context: BotContextTypes) -> None:
    await reply(
        update,
        f"{ic.html('ok')} Keyboard ready – tap a button or type a task.",
        reply_markup=kb.main_reply_keyboard(),
    )


async def help_command(update: Update, context: BotContextTypes) -> None:
    await reply(update, HELP_TEXT, reply_markup=kb.main_reply_keyboard())


async def settings_command(update: Update, context: BotContextTypes) -> None:
    s = app_context(context).settings
    backend = "PostgreSQL" if "postgresql" in s.database_url else "SQLite"
    await reply(
        update,
        f"{ic.html('gear')} <b>Settings</b>\n"
        f"Owner: <code>{s.owner_user_id or 'open'}</code>\n"
        f"DB: {html.escape(backend)}\n"
        f"Gemini: {'on' if s.gemini_enabled else 'off'}\n"
        f"Timezone: {html.escape(str(s.timezone))}\n"
        f"Env: {html.escape(s.environment)}",
        reply_markup=kb.main_reply_keyboard(),
    )


async def note_command(update: Update, context: BotContextTypes) -> None:
    from . import capture

    args = context.args or []
    text = " ".join(args).strip()
    if not text:
        message = update.effective_message
        text = (message.text or "").partition(" ")[2].strip() if message else ""
    if not text:
        await reply(update, f"{ic.html('tip')} Usage: <code>/note text</code>")
        return
    await capture.begin_capture(update, context, text, default_type="note")


async def task_command(update: Update, context: BotContextTypes) -> None:
    from . import capture

    args = context.args or []
    text = " ".join(args).strip()
    if not text:
        await reply(update, f"{ic.html('tip')} Usage: <code>/task text</code>")
        return
    await capture.begin_capture(update, context, text, default_type="task")


async def fallback(update: Update, context: BotContextTypes) -> None:
    if not is_authorised(update, app_context(context).settings):
        return
    await reply(
        update,
        f"{ic.html('tip')} Send text to save a task, or tap /help.",
        reply_markup=kb.main_reply_keyboard(),
    )


async def error_handler(update: object, context: BotContextTypes) -> None:
    logger.exception("Unhandled error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong – please try again."
            )
        except Exception:
            logger.exception("Failed to send error reply")
