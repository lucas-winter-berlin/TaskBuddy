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
from ...services.share import (
    claim_payload,
    claim_url,
    parse_claim_payload,
    telegram_share_url,
)
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
    from_name = update.effective_user.full_name if update.effective_user else None
    bot_username = (context.bot.username or "").lstrip("@")

    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        item = await repo.get_item(uid, item_id)
        if item is None:
            await query.answer("Aufgabe gibt es nicht mehr", show_alert=True)
            return
        project = await repo.get_project(uid, item.project_id)
        subtasks = await repo.list_subtasks(uid, item.id)

    payload = claim_payload(item.id, ctx.settings.telegram_bot_token)
    deep_link = claim_url(bot_username, payload) if bot_username else ""
    html = share_card_text(
        item, project, subtasks, from_name=from_name, claim_url=deep_link or None
    )
    markup = None
    if deep_link:
        markup = keyboards.share_send_keyboard(
            telegram_share_url(
                url=deep_link,
                text=share_card_plain(item, project, subtasks, from_name=from_name),
            )
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

    bot_username = (context.bot.username or "").lstrip("@")
    secret = settings.telegram_bot_token
    from_name = query.from_user.full_name if query.from_user else None
    uid = user_id_of(update)
    ctx = app_context(context)

    try:
        async with ctx.db.session() as session:
            repo = ctx.repository(session)
            items = await repo.find_share_tasks(
                uid, query.query, limit=_SHARE_LIMIT
            )
            projects = {p.id: p for p in await repo.list_projects(uid)}
            results: list[InlineQueryResultArticle] = []
            for item in items:
                subtasks = await repo.list_subtasks(uid, item.id)
                project = projects.get(item.project_id)
                payload = claim_payload(item.id, secret)
                deep_link = claim_url(bot_username, payload) if bot_username else ""
                markup = (
                    keyboards.claim_keyboard(bot_username, payload)
                    if bot_username
                    else None
                )
                description_bits = []
                if project is not None:
                    description_bits.append(project.name)
                if item.priority:
                    description_bits.append(item.priority)
                article: dict = {
                    "id": str(item.id),
                    "title": _article_title(item),
                    "input_message_content": InputTextMessageContent(
                        message_text=share_card_text(
                            item,
                            project,
                            subtasks,
                            from_name=from_name,
                            claim_url=deep_link or None,
                        ),
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    ),
                }
                if description_bits:
                    article["description"] = " · ".join(description_bits)
                if markup is not None:
                    article["reply_markup"] = markup
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
    title = f"#{item.number} {item.title}".strip()
    cleaned = " ".join(title.split())
    if len(cleaned) <= 64:
        return cleaned
    return cleaned[:63] + "…"
