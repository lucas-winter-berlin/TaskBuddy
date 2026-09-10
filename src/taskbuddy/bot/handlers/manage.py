"""Projekte verwalten, Tasks erledigen/loeschen."""

from __future__ import annotations

from telegram import Update

from ... import icons as ic
from ...services.formatting import esc, project_line
from .. import keyboards
from ..context import BotContextTypes, app_context, edit, reply, user_id_of


async def projects_command(update: Update, context: BotContextTypes) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        projects = await repo.ensure_default_projects(uid)
    lines = [f"{ic.html('section')} <b>Projekte</b>"]
    for project in projects:
        lines.append(project_line(project))
    lines.append(
        f"\n{ic.html('tip')} Neu: <code>/project neu Name</code>"
    )
    await reply(update, "\n".join(lines))


async def project_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if len(args) < 2 or args[0].lower() not in {"neu", "new", "add"}:
        await reply(
            update,
            f"{ic.html('tip')} Nutzung: <code>/project neu Name</code>",
        )
        return
    name = " ".join(args[1:]).strip()
    if not name:
        await reply(update, f"{ic.html('warn')} Bitte einen Namen angeben.")
        return
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        await repo.ensure_default_projects(uid)
        existing = await repo.find_project_by_name(uid, name)
        if existing:
            await reply(
                update,
                f"{ic.html('warn')} Gibt’s schon: <b>{esc(existing.name)}</b>",
            )
            return
        project = await repo.create_project(uid, name)
    await reply(
        update,
        f"{ic.html('ok')} Projekt angelegt:\n{project_line(project)}",
    )


async def done_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if not args:
        await reply(update, f"{ic.html('tip')} Nutzung: <code>/done 12</code>")
        return
    raw = args[0].lstrip("#")
    if not raw.isdigit():
        await reply(update, f"{ic.html('warn')} Bitte eine ID, z. B. <code>/done 12</code>")
        return
    await _remove_item(update, context, int(raw), as_done=True)


async def item_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    parts = query.data.split(":")
    if len(parts) != 3:
        return
    _, action, raw_id = parts
    item_id = int(raw_id)
    if action in {"done", "del"}:
        await _remove_item(update, context, item_id, as_done=(action == "done"), via_edit=True)


async def _remove_item(
    update: Update,
    context: BotContextTypes,
    item_id: int,
    *,
    as_done: bool,
    via_edit: bool = False,
) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        item = await repo.get_item(uid, item_id)
        if item is None:
            text = f"{ic.html('warn')} Eintrag <code>#{item_id}</code> nicht gefunden."
            if via_edit:
                await edit(update, text)
            else:
                await reply(update, text)
            return
        if as_done and item.type != "task":
            text = f"{ic.html('warn')} Nur Aufgaben können erledigt werden."
            if via_edit:
                await edit(update, text)
            else:
                await reply(update, text)
            return
        await repo.soft_delete_item(uid, item_id)

    verb = "erledigt und entfernt" if as_done else "gelöscht"
    text = f"{ic.html('ok')} <code>#{item_id}</code> {esc(item.title)} – {verb}."
    if via_edit:
        await edit(update, text)
    else:
        await reply(update, text)
