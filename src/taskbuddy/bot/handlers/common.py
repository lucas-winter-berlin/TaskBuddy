"""Start, Hilfe, Settings, Fallback, Errors."""

from __future__ import annotations

import html
import logging

from telegram import Update

from ... import icons as ic
from ..context import BotContextTypes, app_context, is_authorised, reply, user_id_of

logger = logging.getLogger(__name__)

HELP_TEXT = f"""{ic.html('tip')} <b>TaskBuddy – Commands</b>

Send text → new <b>task</b>
<code>note: …</code> or /note → <b>note</b>

/tasks [project] – tasks (A→D)
/notes [project] – notes
/projects – list projects
/project new Name – create project
/project rename Old -&gt; New
/project delete Name – custom project (+ items)
/done ID – complete task (remove)
/search … – search
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
            f"{ic.html('lock')} Dieser Bot ist privat.\nDeine User-ID: <code>{uid}</code>",
        )
        return

    ctx = app_context(context)
    async with ctx.db.session() as session:
        await ctx.repository(session).ensure_default_projects(user_id_of(update))

    await reply(
        update,
        f"{ic.html('ok')} <b>TaskBuddy</b> bereit.\n"
        f"Schreib eine Aufgabe, z. B.\n"
        f"<code>Rechnung bezahlen – dringend</code>\n\n"
        f"{HELP_TEXT}",
    )


async def help_command(update: Update, context: BotContextTypes) -> None:
    await reply(update, HELP_TEXT)


async def settings_command(update: Update, context: BotContextTypes) -> None:
    s = app_context(context).settings
    backend = "PostgreSQL" if "postgresql" in s.database_url else "SQLite"
    await reply(
        update,
        f"{ic.html('gear')} <b>Settings</b>\n"
        f"Owner: <code>{s.owner_user_id or 'offen'}</code>\n"
        f"DB: {html.escape(backend)}\n"
        f"Gemini: {'an' if s.gemini_enabled else 'aus'}\n"
        f"Timezone: {html.escape(str(s.timezone))}\n"
        f"Env: {html.escape(s.environment)}",
    )


async def note_command(update: Update, context: BotContextTypes) -> None:
    from . import capture

    args = context.args or []
    text = " ".join(args).strip()
    if not text:
        message = update.effective_message
        text = (message.text or "").partition(" ")[2].strip() if message else ""
    if not text:
        await reply(update, f"{ic.html('tip')} Nutzung: <code>/note Text</code>")
        return
    await capture.begin_capture(update, context, text, default_type="note")


async def task_command(update: Update, context: BotContextTypes) -> None:
    from . import capture

    args = context.args or []
    text = " ".join(args).strip()
    if not text:
        await reply(update, f"{ic.html('tip')} Nutzung: <code>/task Text</code>")
        return
    await capture.begin_capture(update, context, text, default_type="task")


async def fallback(update: Update, context: BotContextTypes) -> None:
    if not is_authorised(update, app_context(context).settings):
        return
    await reply(
        update,
        f"{ic.html('tip')} Text senden zum Speichern, oder /help.",
    )


async def error_handler(update: object, context: BotContextTypes) -> None:
    logger.exception("Unbehandelter Fehler: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Interner Fehler – bitte nochmal versuchen."
            )
        except Exception:
            logger.exception("Fehlerantwort fehlgeschlagen")
