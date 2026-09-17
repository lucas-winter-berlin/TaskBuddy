"""Erledigen und Löschen einzelner Aufgaben."""

from __future__ import annotations

from telegram import Update

from ....services.intent import match_by_title, parse_item_id
from ... import copy as txt
from ... import keyboards
from ...context import BotContextTypes, app_context, respond, user_id_of
from .. import query as query_handlers
from .card import show_task_card
from .undo import restore_item


async def done_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if not args:
        await respond(update, txt.DONE_HINT)
        return
    await handle_done_query(update, context, " ".join(args).strip())


async def item_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    parts = query.data.split(":")
    if len(parts) < 3:
        return
    _, action, raw_id, *rest = parts
    if not raw_id.isdigit():
        await query.answer()
        return
    item_id = int(raw_id)
    view_token = rest[0] if rest else None
    if action not in {"done", "del", "edit", "undo"}:
        await query.answer()
        return
    if action == "edit":
        await query.answer()
        await show_task_card(update, context, item_id, via_edit=True)
        return
    if action == "undo":
        await query.answer()
        await restore_item(update, context, item_id, via_edit=True)
        return
    if view_token:
        await remove_item(
            update,
            context,
            item_id,
            as_done=(action == "done"),
            view_token=view_token,
        )
        return
    await query.answer()
    await remove_item(
        update, context, item_id, as_done=(action == "done"), via_edit=True
    )


async def remove_item(
    update: Update,
    context: BotContextTypes,
    item_id: int,
    *,
    as_done: bool,
    via_edit: bool = False,
    view_token: str | None = None,
) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    query = update.callback_query
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        item = await repo.get_item(uid, item_id)
        if item is None:
            if view_token:
                if query is not None:
                    await query.answer()
                await query_handlers.send_task_list(
                    update, context, view_token, via_edit=True
                )
                return
            await respond(update, txt.not_found(item_id), via_edit=via_edit)
            return
        if as_done and item.type != "task":
            if view_token:
                if query is not None:
                    await query.answer(txt.TOAST_NOT_A_TASK, show_alert=True)
                return
            await respond(update, txt.NOT_A_TASK, via_edit=via_edit)
            return
        await repo.soft_delete_item(uid, item_id)

    if view_token:
        if query is not None:
            await query.answer()
        await query_handlers.send_task_list(
            update, context, view_token, via_edit=True
        )
        return

    text = (
        txt.completed(item_id, item.title)
        if as_done
        else txt.deleted(item_id, item.title)
    )
    await respond(update, text, via_edit=via_edit)


async def handle_done_query(
    update: Update, context: BotContextTypes, query: str
) -> None:
    if not query:
        await respond(update, txt.DONE_HINT)
        return
    uid = user_id_of(update)
    ctx = app_context(context)
    item_id = parse_item_id(query)
    if item_id is not None:
        await remove_item(update, context, item_id, as_done=True)
        return

    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        tasks = await repo.list_open_tasks(uid)
        matches = match_by_title(tasks, query)
        subtasks = (
            []
            if matches
            else match_by_title(await repo.list_open_subtasks(uid), query)
        )
        match_ids = [item.id for item in matches]
        sub_rows = [(sub.id, sub.item_id, sub.title) for sub in subtasks]

    if len(match_ids) == 1:
        await remove_item(update, context, match_ids[0], as_done=True)
        return
    if len(match_ids) > 1:
        await respond(
            update,
            txt.ASK_WHICH_TASK,
            reply_markup=keyboards.match_picker("done", matches),
        )
        return
    if len(sub_rows) == 1:
        sub_id, parent_id, title = sub_rows[0]
        async with ctx.db.session() as session:
            await ctx.repository(session).toggle_subtask(uid, sub_id)
        await respond(update, txt.subtask_done(title))
        await show_task_card(update, context, parent_id, via_edit=False)
        return
    if len(sub_rows) > 1:
        await respond(
            update,
            txt.ASK_WHICH_SUBTASK,
            reply_markup=keyboards.subtask_match_picker(subtasks),
        )
        return
    await respond(update, txt.no_match(query))
