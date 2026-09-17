"""Alle offenen Aufgaben löschen."""

from __future__ import annotations

from telegram import Update

from ... import copy as txt
from ... import keyboards, state
from ...context import BotContextTypes, app_context, edit, respond, user_id_of
from .. import query as query_handlers


def _clear_filters(view: state.ListView | None) -> dict:
    if view is None:
        return {"exclude_kind": "backlog"}
    if view.kind == "backlog":
        return {"project_id": view.project_id}
    if view.project_id is not None:
        return {"project_id": view.project_id}
    return {"exclude_kind": "backlog"}


async def clear_command(update: Update, context: BotContextTypes) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    filters = _clear_filters(None)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        page = await repo.list_items(uid, item_type="task", limit=1, **filters)
        count = page.total
    if count == 0:
        await respond(update, txt.EMPTY_CLEAR)
        return
    await respond(
        update,
        txt.confirm_clear(count),
        reply_markup=keyboards.confirm_clear_all(count),
    )


async def clear_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    parts = query.data.split(":")
    if len(parts) < 2:
        return
    _, action, *rest = parts
    token = rest[0] if rest else None
    uid = user_id_of(update)
    ctx = app_context(context)
    view = state.get_view(context.user_data, token) if token else None
    filters = _clear_filters(view)

    if action == "ask":
        async with ctx.db.session() as session:
            repo = ctx.repository(session)
            count = (
                await repo.list_items(uid, item_type="task", limit=1, **filters)
            ).total
        await query.answer()
        if count == 0:
            await edit(update, txt.EMPTY_CLEAR)
            return
        await edit(
            update,
            txt.confirm_clear(count),
            reply_markup=keyboards.confirm_clear_all(count, token),
        )
        return

    if action == "no":
        await query.answer()
        if token:
            await query_handlers.send_task_list(
                update, context, token, via_edit=True
            )
            return
        await edit(update, txt.CANCELLED)
        return

    if action != "yes":
        await query.answer()
        return

    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        removed = await repo.soft_delete_all_tasks(uid, **filters)
    await query.answer()
    if token:
        await query_handlers.send_task_list(update, context, token, via_edit=True)
        return
    await edit(update, txt.deleted_count(removed))
