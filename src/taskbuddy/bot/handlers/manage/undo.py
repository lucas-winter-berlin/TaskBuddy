"""Wiederherstellen erledigter Aufgaben."""

from __future__ import annotations

from telegram import Update

from ....services.formatting import esc
from ....services.intent import match_by_title, parse_item_id
from ... import copy as txt
from ... import keyboards
from ...context import BotContextTypes, app_context, respond, user_id_of
from .card import show_task_card


async def undo_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    await handle_undo_query(update, context, " ".join(args).strip())


async def restore_item(
    update: Update,
    context: BotContextTypes,
    item_id: int,
    *,
    via_edit: bool,
) -> bool:
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        existing = await repo.get_item(uid, item_id)
        if existing is not None:
            await respond(
                update,
                txt.already_open(existing.number, existing.title),
                via_edit=via_edit,
            )
            return False
        item = await repo.restore_item(uid, item_id)
        title = item.title if item else None
        shown = item.number if item else item_id
    if item is None:
        await respond(update, txt.nothing_to_restore(item_id), via_edit=via_edit)
        return False
    await respond(update, txt.restored(shown, title or ""), via_edit=via_edit)
    await show_task_card(update, context, item_id, via_edit=False)
    return True


async def handle_undo_query(
    update: Update, context: BotContextTypes, query: str
) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    raw = (query or "").strip()
    number = parse_item_id(raw) if raw else None
    if number is not None:
        async with ctx.db.session() as session:
            repo = ctx.repository(session)
            deleted = await repo.get_deleted_item_by_number(uid, number)
            if deleted is not None:
                item_id = deleted.id
            else:
                open_item = await repo.get_item_by_number(uid, number)
                if open_item is not None:
                    await respond(
                        update,
                        txt.already_open(open_item.number, open_item.title),
                        via_edit=False,
                    )
                    return
                await respond(update, txt.nothing_to_restore(number), via_edit=False)
                return
        await restore_item(update, context, item_id, via_edit=False)
        return

    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        if not raw:
            items = await repo.list_deleted_tasks(uid, limit=20)
        else:
            items = match_by_title(await repo.list_deleted_tasks(uid), raw)

    if raw and len(items) == 1:
        await restore_item(update, context, items[0].id, via_edit=False)
        return
    await _list_done_tasks(update, items)


async def _list_done_tasks(update: Update, items: list) -> None:
    if not items:
        await respond(update, txt.EMPTY_DONE)
        return
    lines = [txt.DONE_LIST_HEADER, ""]
    for item in items[:20]:
        lines.append(f"<code>#{item.number}</code>  {esc(item.title)}")
    await respond(
        update,
        "\n".join(lines),
        reply_markup=keyboards.restore_list_keyboard(items),
    )
