"""HTML-Formatierung fuer Telegram-Antworten."""

from __future__ import annotations

import html

from .. import icons as ic
from ..db.models import Item, Project
from .priority import LABELS, PRIORITIES, format_priority

_KIND_ORDER = {"private": 0, "work": 1, "backlog": 2}


def esc(value: str | None) -> str:
    return html.escape(value or "")


def project_line(project: Project) -> str:
    return f"{ic.html('section')} <b>{esc(project.name)}</b> <code>{esc(project.key)}</code>"


def task_line(item: Item, project: Project | None = None) -> str:
    """Eine Task-Zeile ohne Prioritaets-Wiederholung (fuer gruppierte Listen)."""
    bits = [f"<code>#{item.id}</code>", esc(item.title)]
    if project is not None:
        bits.append(f"· {esc(project.name)}")
    line = "  ".join((bits[0], " ".join(bits[1:])))
    if item.body:
        line += f"\n<i>{esc(item.body[:200])}</i>"
    return line


def item_line(item: Item, project: Project | None = None) -> str:
    return task_line(item, project)


def _ordered_projects(items: list[Item], projects: dict[int, Project]) -> list[Project]:
    seen_ids = {item.project_id for item in items}
    ordered = sorted(
        (p for p in projects.values() if p.id in seen_ids),
        key=lambda p: (_KIND_ORDER.get(p.kind, 3), p.name.lower()),
    )
    leftover_ids = seen_ids - {p.id for p in ordered}
    for item in items:
        if item.project_id in leftover_ids:
            project = projects.get(item.project_id)
            if project is not None:
                ordered.append(project)
                leftover_ids.discard(item.project_id)
    return ordered


def _priority_blocks(items: list[Item]) -> list[str]:
    blocks: list[str] = []
    for prio in PRIORITIES:
        group = [item for item in items if item.priority == prio]
        if not group:
            continue
        lines = [f"<b>{prio} · {esc(LABELS[prio])}</b>"]
        for item in group:
            lines.append(task_line(item))
        blocks.append("\n".join(lines))
    rest = [item for item in items if item.priority not in PRIORITIES]
    if rest:
        lines = ["<b>Other</b>"]
        for item in rest:
            lines.append(task_line(item))
        blocks.append("\n".join(lines))
    return blocks


def grouped_task_list(
    title: str,
    items: list[Item],
    projects: dict[int, Project],
    *,
    total: int,
    group_by_project: bool = True,
) -> str:
    if not items:
        return f"{ic.html('section')} <b>{esc(title)}</b>\n<i>Nothing here yet.</i>"
    header = f"{ic.html('section')} <b>{esc(title)}</b> ({total})"
    if not group_by_project:
        blocks = _priority_blocks(items)
        return header + "\n\n" + "\n\n\n".join(blocks)

    project_blocks: list[str] = []
    for project in _ordered_projects(items, projects):
        group = [item for item in items if item.project_id == project.id]
        inner = _priority_blocks(group)
        if not inner:
            continue
        body = "\n\n".join(inner)
        project_blocks.append(f"<b>{esc(project.name)}</b>\n\n{body}")
    return header + "\n\n" + "\n\n\n".join(project_blocks)


def draft_summary(
    *,
    title: str,
    body: str | None,
    project_name: str | None,
    priority: str | None,
) -> str:
    lines = [
        f"{ic.html('save')} <b>New Task</b>",
        esc(title),
    ]
    if body:
        lines.append(f"<i>{esc(body[:300])}</i>")
    if project_name:
        lines.append(f"Project: <b>{esc(project_name)}</b>")
    else:
        lines.append("Project: <i>still to choose</i>")
    if priority:
        lines.append(f"Priority: <b>{esc(format_priority(priority))}</b>")
    else:
        lines.append("Priority: <i>still to choose</i>")
    return "\n".join(lines)
