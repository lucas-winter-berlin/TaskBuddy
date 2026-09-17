"""Taskkarte: Anzeige einer Aufgabe mit Checkliste."""

from __future__ import annotations

from telegram import Update

from ....services.formatting import task_card_text
from ... import copy as txt
from ... import keyboards
from ...context import BotContextTypes, app_context, respond, user_id_of


async def show_task_card(
    update: Update,
    context: BotContextTypes,
    item_id: int,
    *,
    via_edit: bool,
) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        item = await repo.get_item(uid, item_id)
        if item is None:
            await respond(update, txt.not_found(item_id), via_edit=via_edit)
            return
        project = await repo.get_project(uid, item.project_id)
        subtasks = await repo.list_subtasks(uid, item.id)
    await respond(
        update,
        task_card_text(item, project, subtasks),
        via_edit=via_edit,
        reply_markup=keyboards.edit_task_keyboard(item.id, subtasks),
    )
