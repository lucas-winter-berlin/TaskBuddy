"""Listen und Suche."""

from __future__ import annotations

from telegram import Update

from ... import icons as ic
from ...services.formatting import esc, item_line
from .. import keyboards, state
from ..context import BotContextTypes, app_context, edit, reply, user_id_of


async def tasks_command(update: Update, context: BotContextTypes) -> None:
    await _list_command(update, context, item_type="task", title="Aufgaben")


async def notes_command(update: Update, context: BotContextTypes) -> None:
    await _list_command(update, context, item_type="note", title="Notizen")


async def search_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if not args:
        await reply(update, f"{ic.html('tip')} Nutzung: <code>/suche Begriff</code>")
        return
    query = " ".join(args).strip()
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        await repo.ensure_default_projects(uid)
        items = await repo.search_items(uid, query, limit=ctx.settings.page_size)
        projects = {p.id: p for p in await repo.list_projects(uid)}

    if not items:
        await reply(update, f"{ic.html('search')} Nichts gefunden für „{esc(query)}“.")
        return
    lines = [f"{ic.html('search')} <b>Suche:</b> {esc(query)}"]
    for item in items:
        lines.append(item_line(item, projects.get(item.project_id)))
    await reply(update, "\n\n".join(lines))


async def _list_command(
    update: Update,
    context: BotContextTypes,
    *,
    item_type: str,
    title: str,
) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    project_filter = None
    args = context.args or []
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        projects = await repo.ensure_default_projects(uid)
        if args:
            name = " ".join(args).strip()
            project = await repo.find_project_by_name(uid, name)
            if project is None:
                await reply(
                    update,
                    f"{ic.html('warn')} Projekt „{esc(name)}“ nicht gefunden.",
                )
                return
            project_filter = project.id
            title = f"{title} · {project.name}"
        page = await repo.list_items(
            uid,
            item_type=item_type,
            project_id=project_filter,
            offset=0,
            limit=ctx.settings.page_size,
        )
        by_id = {p.id: p for p in projects}

    view = state.ListView(
        kind="tasks" if item_type == "task" else "notes",
        project_id=project_filter,
        offset=0,
        title=title,
    )
    token = state.put_view(context.user_data, view)
    await reply(
        update,
        _render_page(title, page, by_id),
        reply_markup=keyboards.pagination(
            token, offset=page.offset, has_prev=page.has_prev, has_next=page.has_next
        ),
    )


def _render_page(title: str, page, projects: dict) -> str:
    if not page.items:
        return f"{ic.html('section')} <b>{esc(title)}</b>\n<i>Noch nichts hier.</i>"
    lines = [
        f"{ic.html('section')} <b>{esc(title)}</b> ({page.total})",
    ]
    for item in page.items:
        lines.append(item_line(item, projects.get(item.project_id)))
    return "\n\n".join(lines)


async def pagination_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    parts = query.data.split(":")
    if len(parts) != 3:
        return
    _, token, direction = parts
    view = state.get_view(context.user_data, token)
    if view is None:
        await edit(update, f"{ic.html('warn')} Liste abgelaufen.")
        return

    ctx = app_context(context)
    step = ctx.settings.page_size
    if direction == "next":
        view.offset += step
    elif direction == "prev":
        view.offset = max(0, view.offset - step)

    uid = user_id_of(update)
    item_type = "task" if view.kind == "tasks" else "note"
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        projects = {p.id: p for p in await repo.list_projects(uid)}
        page = await repo.list_items(
            uid,
            item_type=item_type,
            project_id=view.project_id,
            offset=view.offset,
            limit=step,
        )
    await edit(
        update,
        _render_page(view.title, page, projects),
        reply_markup=keyboards.pagination(
            token, offset=page.offset, has_prev=page.has_prev, has_next=page.has_next
        ),
    )
