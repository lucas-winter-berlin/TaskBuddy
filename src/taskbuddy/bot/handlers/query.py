"""Lists and search."""

from __future__ import annotations

from telegram import Update

from ...services.formatting import grouped_task_list
from ...services.priority import PRIORITIES
from .. import copy as txt
from .. import keyboards, state
from ..context import BotContextTypes, app_context, respond, user_id_of


def parse_tasks_args(args: list[str]) -> tuple[str | None, str | None]:
    """Liefert (priority, project_name). Einzelbuchstaben A–D sind Prioritaet."""
    priority: str | None = None
    project_parts: list[str] = []
    for arg in args:
        upper = arg.upper()
        if upper in PRIORITIES and len(arg) == 1 and priority is None:
            priority = upper
        else:
            project_parts.append(arg)
    name = " ".join(project_parts).strip() or None
    return priority, name


def _list_title(
    kind: str, project_name: str | None, priority: str | None
) -> str:
    return "Backlog" if kind == "backlog" else "Aufgaben"


def _query_kwargs(view: state.ListView) -> dict:
    kwargs: dict = {
        "item_type": "task",
        "project_id": view.project_id,
        "priority": view.priority,
    }
    if view.kind == "tasks" and view.project_id is None:
        kwargs["exclude_kind"] = "backlog"
    return kwargs


async def tasks_command(
    update: Update,
    context: BotContextTypes,
    *,
    args: list[str] | None = None,
) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    priority, project_name = parse_tasks_args(
        list(args if args is not None else context.args or [])
    )
    if project_name and project_name.lower() == "backlog":
        await backlog_command(update, context, args=[priority] if priority else [])
        return

    project_id = None
    stored_project_name = None
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        await repo.ensure_default_projects(uid)
        if project_name:
            project = await repo.find_project_by_name(uid, project_name)
            if project is None:
                await respond(
                    update,
                    txt.project_missing(project_name),
                )
                return
            project_id = project.id
            stored_project_name = project.name

    view = state.ListView(
        kind="tasks",
        project_id=project_id,
        priority=priority,
        argument=stored_project_name or "",
        offset=0,
        title=_list_title("tasks", stored_project_name, priority),
    )
    token = state.put_view(context.user_data, view)
    await send_task_list(update, context, token, via_edit=False)


async def backlog_command(
    update: Update,
    context: BotContextTypes,
    *,
    args: list[str] | None = None,
) -> None:
    uid = user_id_of(update)
    ctx = app_context(context)
    priority, _ = parse_tasks_args(
        list(args if args is not None else context.args or [])
    )
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        await repo.ensure_default_projects(uid)
        backlog = await repo.find_project_by_key(uid, "backlog")
        if backlog is None:
            await respond(update, txt.BACKLOG_MISSING)
            return
        project_id = backlog.id

    view = state.ListView(
        kind="backlog",
        project_id=project_id,
        priority=priority,
        argument="Backlog",
        offset=0,
        title=_list_title("backlog", None, priority),
    )
    token = state.put_view(context.user_data, view)
    await send_task_list(update, context, token, via_edit=False)


async def search_command(update: Update, context: BotContextTypes) -> None:
    args = context.args or []
    if not args:
        await respond(update, txt.SEARCH_HINT)
        return
    await search_with_keyword(update, context, " ".join(args).strip())


async def search_with_keyword(
    update: Update, context: BotContextTypes, keyword: str
) -> None:
    query = keyword.strip()
    if not query:
        await respond(update, txt.SEARCH_HINT)
        return
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        await repo.ensure_default_projects(uid)
        items = await repo.search_items(
            uid, query, item_type="task", limit=ctx.settings.page_size
        )
        counts = await repo.subtask_counts(uid, [item.id for item in items])

    if not items:
        await respond(
            update,
            txt.search_empty(query),
            reply_markup=keyboards.main_reply_keyboard(),
        )
        return
    text = grouped_task_list(items, subtask_counts=counts)
    await respond(
        update,
        text,
        reply_markup=keyboards.main_reply_keyboard(),
    )


async def send_task_list(
    update: Update,
    context: BotContextTypes,
    token: str,
    *,
    via_edit: bool,
) -> None:
    view = state.get_view(context.user_data, token)
    if view is None:
        await respond(update, txt.LIST_EXPIRED, via_edit=via_edit)
        return

    ctx = app_context(context)
    uid = user_id_of(update)
    step = ctx.settings.page_size
    kwargs = _query_kwargs(view)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        page = await repo.list_items(
            uid, offset=view.offset, limit=step, **kwargs
        )
        if not page.items and view.offset > 0:
            view.offset = max(0, view.offset - step)
            page = await repo.list_items(
                uid, offset=view.offset, limit=step, **kwargs
            )
        counts = await repo.subtask_counts(uid, [item.id for item in page.items])

    text = grouped_task_list(page.items, subtask_counts=counts)
    markup = keyboards.task_list_keyboard(
        token,
        page.items,
        has_prev=page.has_prev,
        has_next=page.has_next,
        priority=view.priority,
    )
    await respond(update, text, via_edit=via_edit, reply_markup=markup)


async def pagination_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    parts = query.data.split(":")
    if len(parts) != 3:
        return
    _, token, action = parts
    view = state.get_view(context.user_data, token)
    if view is None:
        await respond(update, txt.LIST_EXPIRED, via_edit=True)
        return

    ctx = app_context(context)
    step = ctx.settings.page_size
    if action == "next":
        view.offset += step
    elif action == "prev":
        view.offset = max(0, view.offset - step)
    elif action == "all":
        if view.priority is None and view.offset == 0:
            return
        view.priority = None
        view.offset = 0
    elif action in PRIORITIES:
        if view.priority == action and view.offset == 0:
            return
        view.priority = action
        view.offset = 0
    else:
        return

    await send_task_list(update, context, token, via_edit=True)
