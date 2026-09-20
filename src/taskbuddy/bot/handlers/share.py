"""Aufgaben in fremde Telegram-Chats teilen (nativer Share + Claim-Link)."""

from __future__ import annotations

import logging

from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ParseMode

from ...services.formatting import share_card_plain, share_card_text
from ...services.share import parse_claim_payload, telegram_share_url
from .. import copy as txt
from .. import keyboards
from ..context import (
    BotContextTypes,
    app_context,
    is_authorised,
    reply,
    user_id_of,
)
from .manage.card import show_task_card

logger = logging.getLogger(__name__)

_SHARE_LIMIT = 20


async def share_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    parts = query.data.split(":")
    if len(parts) != 3 or parts[1] != "go" or not parts[2].isdigit():
        await query.answer()
        return

    item_id = int(parts[2])
    uid = user_id_of(update)
    ctx = app_context(context)

    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        item = await repo.get_item(uid, item_id)
        if item is None:
            await query.answer("Aufgabe gibt es nicht mehr", show_alert=True)
            return
        subtasks = await repo.list_subtasks(uid, item.id)

    html = share_card_text(item, subtasks)
    markup = keyboards.share_send_keyboard(
        telegram_share_url(text=share_card_plain(item, subtasks))
    )
    await query.answer(txt.SHARE_TOAST)
    await reply(update, html, reply_markup=markup)


async def inline_query(update: Update, context: BotContextTypes) -> None:
    query = update.inline_query
    if query is None:
        return
    settings = app_context(context).settings
    if not is_authorised(update, settings):
        await query.answer([], cache_time=0, is_personal=True)
        return

    uid = user_id_of(update)
    ctx = app_context(context)

    try:
        async with ctx.db.session() as session:
            repo = ctx.repository(session)
            items = await repo.find_share_tasks(
                uid, query.query, limit=_SHARE_LIMIT
            )
            results: list[InlineQueryResultArticle] = []
            for item in items:
                subtasks = await repo.list_subtasks(uid, item.id)
                article: dict = {
                    "id": str(item.id),
                    "title": _article_title(item),
                    "input_message_content": InputTextMessageContent(
                        message_text=share_card_text(item, subtasks),
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    ),
                }
                results.append(InlineQueryResultArticle(**article))
        await query.answer(results, cache_time=5, is_personal=True)
    except Exception:
        logger.exception("Inline-Query fehlgeschlagen")
        await query.answer([], cache_time=0, is_personal=True)


async def handle_claim(
    update: Update, context: BotContextTypes, payload: str
) -> None:
    ctx = app_context(context)
    item_id = parse_claim_payload(payload, ctx.settings.telegram_bot_token)
    if item_id is None:
        await reply(update, txt.CLAIM_BAD, reply_markup=keyboards.main_reply_keyboard())
        return

    uid = user_id_of(update)
    copied_notice: tuple[int, str] | None = None
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        source = await repo.get_item_by_id(item_id)
        if source is None:
            await reply(
                update, txt.CLAIM_GONE, reply_markup=keyboards.main_reply_keyboard()
            )
            return
        if source.user_id == uid:
            target_id = source.id
        else:
            copied = await repo.copy_task_to_user(source, uid)
            copied_notice = (copied.number, copied.title)
            target_id = copied.id

    if copied_notice is not None:
        await reply(
            update,
            txt.claimed(*copied_notice),
            reply_markup=keyboards.main_reply_keyboard(),
        )
    await show_task_card(update, context, target_id, via_edit=False)


def _article_title(item) -> str:
    cleaned = " ".join((item.title or "").split())
    if len(cleaned) <= 64:
        return cleaned or "Aufgabe"
    return cleaned[:63] + "…"
