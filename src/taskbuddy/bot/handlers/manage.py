"""Manage projects, complete/delete tasks."""

from __future__ import annotations

from telegram import Update

from ... import icons as ic
from ...services.formatting import esc, project_line
from .. import keyboards
from ..context import BotContextTypes, app_context, edit, reply, user_id_of

_PROJECT_USAGE = (
    f"{ic.html('tip')} Usage:\n"
    f"<code>/project new Name</code>\n"
    f"<code>/project rename Old -&gt; New</code>\n"
    f"<code>/project delete Name</code>\n"
    f"(Privat/Arbeit cannot be deleted.)"
)


async def projects_command(update: Update, context: BotContextTypes) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        projects = await repo.ensure_default_projects(uid)
    lines = [f"{ic.html('section')} <b>Projects</b>"]
    for project in projects:
        lines.append(project_line(project))
    lines.append(f"\n{_PROJECT_USAGE}")
    await reply(
        update,
        "\n".join(lines),
        reply_markup=keyboards.main_reply_keyboard(),
    )


async def project_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if not args:
        await reply(update, _PROJECT_USAGE)
        return

    action = args[0].lower()
    rest = args[1:]

    if action in {"new", "add", "neu"}:
        await _project_create(update, context, " ".join(rest).strip())
        return
    if action in {"delete", "del", "remove", "rm", "löschen", "loeschen"}:
        await _project_delete(update, context, " ".join(rest).strip())
        return
    if action in {"rename", "ren", "umbenennen"}:
        await _project_rename(update, context, " ".join(rest).strip())
        return

    await reply(update, _PROJECT_USAGE)


async def _project_create(
    update: Update, context: BotContextTypes, name: str
) -> None:
    if not name:
        await reply(update, f"{ic.html('warn')} Please provide a name.")
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
                f"{ic.html('warn')} Already exists: <b>{esc(existing.name)}</b>",
            )
            return
        project = await repo.create_project(uid, name)
    await reply(
        update,
        f"{ic.html('ok')} Project created:\n{project_line(project)}",
    )


async def _project_delete(
    update: Update, context: BotContextTypes, name: str
) -> None:
    if not name:
        await reply(
            update,
            f"{ic.html('tip')} Usage: <code>/project delete Name</code>",
        )
        return
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        await repo.ensure_default_projects(uid)
        project = await repo.find_project_by_name(uid, name)
        if project is None:
            await reply(
                update,
                f"{ic.html('warn')} Project \"{esc(name)}\" not found.",
            )
            return
        if project.kind in ("private", "work"):
            await reply(
                update,
                f"{ic.html('lock')} <b>{esc(project.name)}</b> is built-in – "
                f"cannot be deleted (rename only).",
            )
            return
        removed = await repo.soft_delete_project(uid, project.id)
    await reply(
        update,
        f"{ic.html('ok')} Project <b>{esc(project.name)}</b> deleted"
        f" ({removed or 0} items removed too).",
    )


async def _project_rename(
    update: Update, context: BotContextTypes, raw: str
) -> None:
    if "->" not in raw and "→" not in raw:
        await reply(
            update,
            f"{ic.html('tip')} Usage: "
            f"<code>/project rename Old -&gt; New</code>",
        )
        return
    sep = "->" if "->" in raw else "→"
    old_name, _, new_name = raw.partition(sep)
    old_name, new_name = old_name.strip(), new_name.strip()
    if not old_name or not new_name:
        await reply(
            update,
            f"{ic.html('warn')} Old and new name required "
            f"(<code>Old -&gt; New</code>).",
        )
        return

    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        await repo.ensure_default_projects(uid)
        project = await repo.find_project_by_name(uid, old_name)
        if project is None:
            await reply(
                update,
                f"{ic.html('warn')} Project \"{esc(old_name)}\" not found.",
            )
            return
        try:
            updated = await repo.rename_project(uid, project.id, new_name)
        except ValueError as exc:
            await reply(update, f"{ic.html('warn')} {esc(str(exc))}")
            return
    await reply(
        update,
        f"{ic.html('ok')} Renamed:\n{project_line(updated)}",
    )


async def done_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if not args:
        await reply(update, f"{ic.html('tip')} Usage: <code>/done 12</code>")
        return
    raw = args[0].lstrip("#")
    if not raw.isdigit():
        await reply(
            update, f"{ic.html('warn')} Please provide an ID, e.g. <code>/done 12</code>"
        )
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
            text = f"{ic.html('warn')} Item <code>#{item_id}</code> not found."
            if via_edit:
                await edit(update, text)
            else:
                await reply(update, text)
            return
        if as_done and item.type != "task":
            text = f"{ic.html('warn')} Only tasks can be marked done."
            if via_edit:
                await edit(update, text)
            else:
                await reply(update, text)
            return
        await repo.soft_delete_item(uid, item_id)

    verb = "done and removed" if as_done else "deleted"
    text = f"{ic.html('ok')} <code>#{item_id}</code> {esc(item.title)} – {verb}."
    if via_edit:
        await edit(update, text)
    else:
        await reply(update, text)
