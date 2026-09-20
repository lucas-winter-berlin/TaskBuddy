"""Aufbau der Telegram-Application."""

from __future__ import annotations

import logging

from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeDefault
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    Defaults,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from ..config import Settings
from ..db import Database
from ..services.gemini import GeminiClassifier
from . import keyboards
from .context import AppContext, BotContextTypes, app_context, is_authorised
from .handlers import common, manage, query, router, share

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("tasks", "Aufgaben"),
    BotCommand("backlog", "Backlog"),
    BotCommand("done", "Erledigen"),
    BotCommand("edit", "Öffnen"),
    BotCommand("undo", "Wiederherstellen"),
    BotCommand("clear", "Alle löschen"),
    BotCommand("search", "Suchen"),
    BotCommand("settings", "Einstellungen"),
    BotCommand("help", "Hilfe"),
    BotCommand("menu", "Tastatur"),
]


def build_application(settings: Settings, database: Database) -> Application:
    classifier = (
        GeminiClassifier(settings.gemini_api_key, settings.gemini_model)
        if settings.gemini_enabled
        else None
    )
    app_ctx = AppContext(settings=settings, db=database, classifier=classifier)

    application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .defaults(Defaults(tzinfo=settings.timezone))
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    application.bot_data["app_context"] = app_ctx

    allowed = (
        filters.User(user_id=settings.owner_user_id)
        if settings.owner_user_id is not None
        else filters.ALL
    )

    _register_commands(application, allowed)
    _register_callbacks(application)
    application.add_handler(InlineQueryHandler(share.inline_query))

    application.add_handler(
        MessageHandler(
            allowed & (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            router.text_router,
        )
    )
    application.add_handler(MessageHandler(filters.ALL, common.fallback))
    application.add_error_handler(common.error_handler)
    return application


def _guarded(callback):
    async def wrapper(update, context: BotContextTypes) -> None:
        if not is_authorised(update, app_context(context).settings):
            await _reject_callback(update, context)
            return
        await callback(update, context)

    wrapper.__name__ = getattr(callback, "__name__", "guarded_callback")
    return wrapper


def _register_commands(application: Application, allowed) -> None:
    # /start ohne Owner-Filter, damit Claim-Links ankommen;
    # Unberechtigte sieht start() selbst ab.
    application.add_handler(CommandHandler("start", common.start))
    handlers = [
        ("help", common.help_command),
        ("menu", common.menu_command),
        ("settings", common.settings_command),
        ("task", common.task_command),
        ("tasks", query.tasks_command),
        ("backlog", query.backlog_command),
        ("search", query.search_command),
        ("done", manage.done_command),
        ("edit", manage.edit_command),
        ("undo", manage.undo_command),
        ("clear", manage.clear_command),
    ]
    for name, callback in handlers:
        application.add_handler(CommandHandler(name, callback, filters=allowed))


def _register_callbacks(application: Application) -> None:
    from .handlers import capture

    routes = [
        (keyboards.CAP, capture.capture_callback),
        (keyboards.ITEM, manage.item_callback),
        (keyboards.EDT, manage.edit_callback),
        (keyboards.PAGE, query.pagination_callback),
        (keyboards.CLR, manage.clear_callback),
        (keyboards.SHR, share.share_callback),
    ]
    for prefix, callback in routes:
        application.add_handler(
            CallbackQueryHandler(_guarded(callback), pattern=rf"^{prefix}:")
        )


async def _reject_callback(update, context) -> None:
    if update.callback_query is not None:
        await update.callback_query.answer("Dieser Bot ist privat.", show_alert=True)


async def _clear_and_set_commands(bot) -> None:
    """Alte Slash-Befehle entfernen, dann die aktuelle Liste setzen."""
    for scope in (BotCommandScopeDefault(), BotCommandScopeAllPrivateChats()):
        await bot.delete_my_commands(scope=scope)
    await bot.set_my_commands(BOT_COMMANDS)


async def _post_init(application: Application) -> None:
    ctx: AppContext = application.bot_data["app_context"]
    await ctx.db.create_schema()
    await _clear_and_set_commands(application.bot)
    me = await application.bot.get_me()
    logger.info("Bot @%s ist bereit", me.username)


async def _post_shutdown(application: Application) -> None:
    ctx: AppContext = application.bot_data["app_context"]
    await ctx.db.dispose()
    logger.info("Datenbank-Verbindungen geschlossen")
