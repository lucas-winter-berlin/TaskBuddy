"""Capture tasks/notes including confirmation."""

from __future__ import annotations

import logging

from telegram import Update

from ... import icons as ic
from ...services.classify import guess_project, parse_input
from ...services.formatting import draft_summary, esc
from ...services.priority import guess_priority
from .. import keyboards, state
from ..context import BotContextTypes, app_context, edit, reply, user_id_of

logger = logging.getLogger(__name__)


async def begin_capture(
    update: Update,
    context: BotContextTypes,
    text: str,
    *,
    default_type: str = "task",
) -> None:
    settings = app_context(context).settings
    parsed = parse_input(text, default_type=default_type)
    if not parsed.title:
        await reply(update, f"{ic.html('warn')} Please provide text for the task/note.")
        return
    if len(parsed.title) > settings.max_title_length:
        await reply(update, f"{ic.html('warn')} Title too long.")
        return

    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        projects = await repo.ensure_default_projects(uid)

    draft = state.Draft(
        item_type=parsed.item_type,
        title=parsed.title[: settings.max_title_length],
        body=(parsed.body[: settings.max_body_length] if parsed.body else None),
    )

    # Heuristic
    proj_guess = guess_project(
        f"{parsed.title}\n{parsed.body or ''}",
        projects,
    )
    prio_guess = (
        guess_priority(f"{parsed.title}\n{parsed.body or ''}")
        if parsed.item_type == "task"
        else None
    )

    # Optional Gemini
    if ctx.classifier is not None:
        ai = await ctx.classifier.classify(
            text=f"{parsed.title}\n{parsed.body or ''}",
            item_type=parsed.item_type,
            projects=[(p.id, p.name, p.kind) for p in projects],
        )
        if ai:
            ai_conf = float(ai.get("confidence") or 0)
            if ai.get("project_id") and ai_conf >= proj_guess.confidence:
                draft.project_id = int(ai["project_id"])
                draft.project_confidence = ai_conf
            if (
                parsed.item_type == "task"
                and ai.get("priority")
                and ai_conf >= (prio_guess.confidence if prio_guess else 0)
            ):
                draft.priority = str(ai["priority"])
                draft.priority_confidence = ai_conf

    if draft.project_id is None and proj_guess.project_id is not None:
        draft.project_id = proj_guess.project_id
        draft.project_confidence = proj_guess.confidence
    if (
        parsed.item_type == "task"
        and draft.priority is None
        and prio_guess
        and prio_guess.priority
    ):
        draft.priority = prio_guess.priority
        draft.priority_confidence = prio_guess.confidence

    threshold = settings.classify_confidence_threshold
    need_project = (
        draft.project_id is None or draft.project_confidence < threshold
    )
    need_priority = parsed.item_type == "task" and (
        draft.priority is None or draft.priority_confidence < threshold
    )

    token = state.put_draft(context.user_data, draft)
    project_name = next(
        (p.name for p in projects if p.id == draft.project_id),
        None,
    )

    if need_project:
        draft.awaiting = "project"
        await reply(
            update,
            draft_summary(
                item_type=draft.item_type,
                title=draft.title,
                body=draft.body,
                project_name=project_name,
                priority=draft.priority,
            )
            + f"\n\n{ic.html('tip')} Which project?",
            reply_markup=keyboards.project_picker(token, projects),
        )
        return

    if need_priority:
        draft.awaiting = "priority"
        await reply(
            update,
            draft_summary(
                item_type=draft.item_type,
                title=draft.title,
                body=draft.body,
                project_name=project_name,
                priority=draft.priority,
            )
            + f"\n\n{ic.html('tip')} Which priority?",
            reply_markup=keyboards.priority_picker(token),
        )
        return

    draft.awaiting = "confirm"
    markup = (
        keyboards.confirm_draft(token)
        if draft.item_type == "task"
        else keyboards.confirm_note(token)
    )
    await reply(
        update,
        draft_summary(
            item_type=draft.item_type,
            title=draft.title,
            body=draft.body,
            project_name=project_name,
            priority=draft.priority,
        )
        + f"\n\n{ic.html('tip')} Does this look right?",
        reply_markup=markup,
    )


async def capture_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    parts = query.data.split(":")
    # cap:action:token[:extra]
    if len(parts) < 3:
        return
    _, action, token, *rest = parts
    draft = state.get_draft(context.user_data, token)
    if draft is None:
        await edit(update, f"{ic.html('warn')} Draft expired – please send again.")
        return

    uid = user_id_of(update)
    ctx = app_context(context)

    if action == "cancel":
        state.drop_draft(context.user_data, token)
        state.set_pending(context.user_data, None)
        await edit(update, f"{ic.html('no')} Cancelled.")
        return

    if action == "newproj":
        draft.awaiting = "new_project"
        state.set_pending(
            context.user_data, state.Pending(kind="new_project", ref=token)
        )
        await edit(
            update,
            f"{ic.html('edit')} Send a name for the new project:",
        )
        return

    if action == "reproj":
        async with ctx.db.session() as session:
            projects = await ctx.repository(session).ensure_default_projects(uid)
        draft.awaiting = "project"
        await edit(
            update,
            await _summary_for(draft, ctx, uid) + f"\n\n{ic.html('tip')} Which project?",
            reply_markup=keyboards.project_picker(token, projects),
        )
        return

    if action == "reprio":
        if draft.item_type != "task":
            return
        draft.awaiting = "priority"
        await edit(
            update,
            await _summary_for(draft, ctx, uid) + f"\n\n{ic.html('tip')} Which priority?",
            reply_markup=keyboards.priority_picker(token),
        )
        return

    if action == "proj" and rest:
        draft.project_id = int(rest[0])
        draft.project_confidence = 1.0
        await _advance_after_project(update, context, token, draft)
        return

    if action == "prio" and rest:
        draft.priority = rest[0]
        draft.priority_confidence = 1.0
        await _show_confirm(update, context, token, draft)
        return

    if action == "save":
        await _persist(update, context, token, draft)
        return


async def handle_new_project_name(
    update: Update, context: BotContextTypes, token: str, name: str
) -> None:
    draft = state.get_draft(context.user_data, token)
    if draft is None:
        await reply(update, f"{ic.html('warn')} Draft expired.")
        return
    name = name.strip()
    if not name:
        await reply(update, f"{ic.html('warn')} Please send a name.")
        return
    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        project = await repo.create_project(uid, name)
        draft.project_id = project.id
        draft.project_confidence = 1.0
    state.set_pending(context.user_data, None)
    # After project: priority or confirm
    threshold = ctx.settings.classify_confidence_threshold
    need_priority = draft.item_type == "task" and (
        draft.priority is None or draft.priority_confidence < threshold
    )
    if need_priority:
        draft.awaiting = "priority"
        await reply(
            update,
            await _summary_for(draft, ctx, uid)
            + f"\n\n{ic.html('ok')} Project <b>{esc(name)}</b> created.\n"
            f"{ic.html('tip')} Which priority?",
            reply_markup=keyboards.priority_picker(token),
        )
        return
    await reply(
        update,
        await _summary_for(draft, ctx, uid)
        + f"\n\n{ic.html('ok')} Project <b>{esc(name)}</b> created.\n"
        f"{ic.html('tip')} Does this look right?",
        reply_markup=(
            keyboards.confirm_draft(token)
            if draft.item_type == "task"
            else keyboards.confirm_note(token)
        ),
    )


async def _advance_after_project(
    update: Update, context: BotContextTypes, token: str, draft: state.Draft
) -> None:
    ctx = app_context(context)
    uid = user_id_of(update)
    threshold = ctx.settings.classify_confidence_threshold
    need_priority = draft.item_type == "task" and (
        draft.priority is None or draft.priority_confidence < threshold
    )
    if need_priority:
        draft.awaiting = "priority"
        await edit(
            update,
            await _summary_for(draft, ctx, uid) + f"\n\n{ic.html('tip')} Which priority?",
            reply_markup=keyboards.priority_picker(token),
        )
        return
    await _show_confirm(update, context, token, draft)


async def _show_confirm(
    update: Update, context: BotContextTypes, token: str, draft: state.Draft
) -> None:
    ctx = app_context(context)
    uid = user_id_of(update)
    draft.awaiting = "confirm"
    markup = (
        keyboards.confirm_draft(token)
        if draft.item_type == "task"
        else keyboards.confirm_note(token)
    )
    await edit(
        update,
        await _summary_for(draft, ctx, uid) + f"\n\n{ic.html('tip')} Does this look right?",
        reply_markup=markup,
    )


async def _persist(
    update: Update, context: BotContextTypes, token: str, draft: state.Draft
) -> None:
    if draft.project_id is None:
        await edit(update, f"{ic.html('warn')} Project still missing.")
        return
    if draft.item_type == "task" and not draft.priority:
        await edit(update, f"{ic.html('warn')} Priority still missing.")
        return

    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        item = await repo.create_item(
            user_id=uid,
            project_id=draft.project_id,
            item_type=draft.item_type,
            title=draft.title,
            body=draft.body,
            priority=draft.priority,
        )
        project = await repo.get_project(uid, draft.project_id)

    state.drop_draft(context.user_data, token)
    kind = "Task" if draft.item_type == "task" else "Note"
    extra = f" [{draft.priority}]" if draft.priority else ""
    await edit(
        update,
        f"{ic.html('ok')} {kind} saved{extra}\n"
        f"<code>#{item.id}</code> {esc(item.title)}\n"
        f"Project: <b>{esc(project.name if project else '?')}</b>",
        reply_markup=keyboards.item_actions(item.id, is_task=draft.item_type == "task"),
    )


async def _summary_for(draft: state.Draft, ctx, uid: int) -> str:
    project_name = None
    if draft.project_id is not None:
        async with ctx.db.session() as session:
            project = await ctx.repository(session).get_project(uid, draft.project_id)
            if project:
                project_name = project.name
    return draft_summary(
        item_type=draft.item_type,
        title=draft.title,
        body=draft.body,
        project_name=project_name,
        priority=draft.priority,
    )
