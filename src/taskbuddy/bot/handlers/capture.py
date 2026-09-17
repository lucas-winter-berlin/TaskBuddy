"""Neue Aufgaben erfassen und bestätigen."""

from __future__ import annotations

from telegram import Update

from ...services.classify import guess_project, parse_input
from ...services.formatting import draft_summary
from ...services.intent import split_notes_and_subtasks
from ...services.priority import guess_priority
from .. import copy as txt
from .. import keyboards, state
from ..context import BotContextTypes, app_context, respond, user_id_of
from . import manage


async def begin_capture(
    update: Update,
    context: BotContextTypes,
    text: str,
) -> None:
    settings = app_context(context).settings
    parsed = parse_input(text)
    if not parsed.title:
        await respond(update, txt.TITLE_MISSING)
        return
    if len(parsed.title) > settings.max_title_length:
        await respond(update, txt.TITLE_TOO_LONG)
        return

    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        projects = await ctx.repository(session).ensure_default_projects(uid)

    notes, checklist = split_notes_and_subtasks(parsed.body)
    draft = state.Draft(
        title=parsed.title[: settings.max_title_length],
        body=(notes[: settings.max_body_length] if notes else None),
        subtasks=checklist,
    )
    combined = f"{parsed.title}\n{notes or ''}"
    await _fill_guesses(draft, combined, projects, ctx)
    token = state.put_draft(context.user_data, draft)
    await _prompt_next(update, context, token, draft, projects, via_edit=False)


async def capture_callback(update: Update, context: BotContextTypes) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    parts = query.data.split(":")
    if len(parts) < 3:
        return
    _, action, token, *rest = parts
    draft = state.get_draft(context.user_data, token)
    if draft is None:
        await respond(update, txt.DRAFT_EXPIRED, via_edit=True)
        return

    uid = user_id_of(update)
    ctx = app_context(context)

    if action == "cancel":
        state.drop_draft(context.user_data, token)
        state.set_pending(context.user_data, None)
        await respond(update, txt.CANCELLED, via_edit=True)
        return

    if action == "reproj":
        async with ctx.db.session() as session:
            projects = await ctx.repository(session).ensure_default_projects(uid)
        await _ask_project(update, context, token, draft, projects)
        return

    if action == "reprio":
        await _ask_priority(update, context, token, draft)
        return

    if action == "proj" and rest:
        draft.project_id = int(rest[0])
        draft.project_confidence = 1.0
        async with ctx.db.session() as session:
            projects = await ctx.repository(session).ensure_default_projects(uid)
        await _prompt_next(update, context, token, draft, projects, via_edit=True)
        return

    if action == "prio" and rest:
        draft.priority = rest[0]
        draft.priority_confidence = 1.0
        await _show_confirm(update, context, token, draft)
        return

    if action == "save":
        await _persist(update, context, token, draft)


async def _fill_guesses(draft: state.Draft, combined: str, projects, ctx) -> None:
    proj_guess = guess_project(combined, projects)
    prio_guess = guess_priority(combined)

    if ctx.classifier is not None:
        ai = await ctx.classifier.classify(
            text=combined,
            item_type="task",
            projects=[(p.id, p.name, p.kind) for p in projects],
        )
        if ai:
            ai_conf = float(ai.get("confidence") or 0)
            if ai.get("project_id") and ai_conf >= proj_guess.confidence:
                draft.project_id = int(ai["project_id"])
                draft.project_confidence = ai_conf
            if ai.get("priority") and ai_conf >= prio_guess.confidence:
                draft.priority = str(ai["priority"])
                draft.priority_confidence = ai_conf

    if draft.project_id is None and proj_guess.project_id is not None:
        draft.project_id = proj_guess.project_id
        draft.project_confidence = proj_guess.confidence
    if draft.priority is None and prio_guess.priority:
        draft.priority = prio_guess.priority
        draft.priority_confidence = prio_guess.confidence


async def _prompt_next(
    update, context, token: str, draft: state.Draft, projects, *, via_edit: bool
) -> None:
    threshold = app_context(context).settings.classify_confidence_threshold
    need_project = draft.project_id is None or draft.project_confidence < threshold
    need_priority = draft.priority is None or draft.priority_confidence < threshold
    if need_project:
        await _ask_project(
            update, context, token, draft, projects, via_edit=via_edit
        )
        return
    if need_priority:
        await _ask_priority(update, context, token, draft, via_edit=via_edit)
        return
    await _show_confirm(update, context, token, draft, via_edit=via_edit)


async def _ask_project(
    update, context, token, draft, projects, *, via_edit: bool = True
) -> None:
    draft.awaiting = "project"
    await respond(
        update,
        await _summary_for(update, context, draft) + f"\n\n{txt.ASK_PROJECT}",
        via_edit=via_edit,
        reply_markup=keyboards.project_picker(token, projects),
    )


async def _ask_priority(
    update, context, token, draft, *, via_edit: bool = True
) -> None:
    draft.awaiting = "priority"
    await respond(
        update,
        await _summary_for(update, context, draft) + f"\n\n{txt.ASK_PRIORITY}",
        via_edit=via_edit,
        reply_markup=keyboards.priority_picker(token),
    )


async def _show_confirm(
    update, context, token, draft, *, via_edit: bool = True
) -> None:
    draft.awaiting = "confirm"
    await respond(
        update,
        await _summary_for(update, context, draft) + f"\n\n{txt.ASK_CONFIRM}",
        via_edit=via_edit,
        reply_markup=keyboards.confirm_draft(token),
    )


async def _persist(
    update: Update, context: BotContextTypes, token: str, draft: state.Draft
) -> None:
    if draft.project_id is None:
        await respond(update, txt.SAVED_MISSING_PROJECT, via_edit=True)
        return
    if not draft.priority:
        await respond(update, txt.SAVED_MISSING_PRIORITY, via_edit=True)
        return

    uid = user_id_of(update)
    ctx = app_context(context)
    async with ctx.db.session() as session:
        repo = ctx.repository(session)
        item = await repo.create_item(
            user_id=uid,
            project_id=draft.project_id,
            item_type="task",
            title=draft.title,
            body=draft.body,
            priority=draft.priority,
        )
        if draft.subtasks:
            await repo.add_subtasks(uid, item.id, draft.subtasks)

    state.drop_draft(context.user_data, token)
    await manage.show_task_card(update, context, item.id, via_edit=True)


async def _summary_for(update, context, draft: state.Draft) -> str:
    uid = user_id_of(update)
    ctx = app_context(context)
    project_name = None
    if draft.project_id is not None:
        async with ctx.db.session() as session:
            project = await ctx.repository(session).get_project(uid, draft.project_id)
            if project:
                project_name = project.name
    return draft_summary(
        title=draft.title,
        body=draft.body,
        project_name=project_name,
        priority=draft.priority,
        subtasks=draft.subtasks,
    )
