"""Bearbeiten von Titel, Notizen, Priorität, Projekt und Checkliste."""

from __future__ import annotations

from telegram import Update

from ....services.intent import match_by_title, parse_item_id
from ... import copy as txt
from ... import keyboards, state
from ...context import BotContextTypes, app_context, edit, respond, user_id_of
from .card import show_task_card


async def edit_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if not args:
        await respond(update, txt.EDIT_HINT)
        return
    await handle_edit_query(update, context, " ".join(args).strip())


async def handle_edit_query(
    update: Update, context: BotContextTypes, query: str
) -> None:
    if not query:
        await respond(update, txt.EDIT_HINT)
        return
    uid = user_id_of(update)
    ctx = app_context(context)
    number = parse_item_id(query)
    if number is not None:
        async with ctx.db.session() as session:
            item = await ctx.repository(session).get_item_by_number(uid, number)
            item_id = item.id if item else None
        if item_id is None:
            await respond(update, txt.not_found(number))
            return
        await show_task_card(update, context, item_id, via_edit=False)
        return
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        matches = match_by_title(await repo.list_open_tasks(uid), query)
    if len(matches) == 1:
        await show_task_card(update, context, matches[0].id, via_edit=False)
        return
    if len(matches) > 1:
        await respond(
            update,
            txt.ASK_WHICH_TASK,
            reply_markup=keyboards.match_picker("edit", matches),
        )
        return
    await respond(update, txt.no_match(query))


async def apply_pending_edit(
    update: Update, context: BotContextTypes, pending: state.Pending, text: str
) -> bool:
    if pending.kind not in {"edit_title", "edit_notes", "edit_subtask"}:
        return False
    if not pending.ref.isdigit():
        state.set_pending(context.user_data, None)
        return False
    item_id = int(pending.ref)
    uid = user_id_of(update)
    ctx = app_context(context)
    cleaned = text.strip()
    if not cleaned:
        await respond(update, txt.TEXT_MISSING)
        return True
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        try:
            if pending.kind == "edit_title":
                await repo.update_item(uid, item_id, title=cleaned)
            elif pending.kind == "edit_notes":
                await repo.update_item(uid, item_id, body=cleaned)
            else:
                await repo.add_subtasks(uid, item_id, [(cleaned, False)])
        except ValueError as exc:
            await respond(update, txt.warning(str(exc)))
            return True
    state.set_pending(context.user_data, None)
    await show_task_card(update, context, item_id, via_edit=False)
    return True


async def edit_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    parts = query.data.split(":")
    if len(parts) < 3:
        await query.answer()
        return
    _, action, raw_id, *rest = parts
    if action == "noop":
        await query.answer()
        await edit(update, txt.CANCELLED)
        return
    if not raw_id.isdigit():
        await query.answer()
        return
    item_id = int(raw_id)
    uid = user_id_of(update)
    ctx = app_context(context)

    if action == "close":
        state.set_pending(context.user_data, None)
        await query.answer()
        await edit(update, txt.CLOSED)
        return

    if action == "show":
        await query.answer()
        await show_task_card(update, context, item_id, via_edit=True)
        return

    prompts = {
        "title": ("edit_title", txt.ASK_TITLE),
        "notes": ("edit_notes", txt.ASK_NOTES),
        "add": ("edit_subtask", txt.ASK_SUBTASK),
    }
    if action in prompts:
        kind, prompt = prompts[action]
        state.set_pending(
            context.user_data, state.Pending(kind=kind, ref=str(item_id))
        )
        await query.answer()
        kwargs = {}
        if action == "title":
            kwargs["reply_markup"] = keyboards.edit_task_keyboard(item_id, [])
        await edit(update, prompt, **kwargs)
        return

    if action == "prio":
        await query.answer()
        await edit(
            update,
            txt.ASK_PRIORITY,
            reply_markup=keyboards.edit_priority_picker(item_id),
        )
        return

    if action == "proj":
        async with ctx.db.session() as session:
            projects = await ctx.repository(session).ensure_default_projects(uid)
        await query.answer()
        await edit(
            update,
            txt.ASK_PROJECT,
            reply_markup=keyboards.edit_project_picker(item_id, projects),
        )
        return

    if action == "setr" and rest:
        async with ctx.db.session() as session:
            try:
                await ctx.repository(session).update_item(
                    uid, item_id, priority=rest[0]
                )
            except ValueError as exc:
                await query.answer(str(exc), show_alert=True)
                return
        await query.answer()
        await show_task_card(update, context, item_id, via_edit=True)
        return

    if action == "setp" and rest and rest[0].isdigit():
        async with ctx.db.session() as session:
            try:
                await ctx.repository(session).update_item(
                    uid, item_id, project_id=int(rest[0])
                )
            except ValueError as exc:
                await query.answer(str(exc), show_alert=True)
                return
        await query.answer()
        await show_task_card(update, context, item_id, via_edit=True)
        return

    if action == "tog" and rest and rest[0].isdigit():
        async with ctx.db.session() as session:
            row = await ctx.repository(session).toggle_subtask(uid, int(rest[0]))
        if row is None:
            await query.answer()
            return
        await query.answer()
        await show_task_card(update, context, row.item_id, via_edit=True)
        return

    await query.answer()
