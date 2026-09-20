"""HTML-Formatierung fuer Telegram-Antworten."""

from __future__ import annotations

import html

from ..db.models import Item, Project
from .priority import LABELS, PRIORITIES, format_priority


def esc(value: str | None) -> str:
    return html.escape(value or "")


def task_line(
    item: Item,
    project: Project | None = None,
    *,
    subtasks: tuple[int, int] | None = None,
) -> str:
    """Eine Task-Zeile ohne Prioritaets-Wiederholung (fuer gruppierte Listen)."""
    bits = [f"<code>#{item.number}</code>", esc(item.title)]
    if subtasks and subtasks[1]:
        bits.append(f"{subtasks[0]}/{subtasks[1]}")
    if project is not None:
        bits.append(f"· {esc(project.name)}")
    line = "  ".join((bits[0], " ".join(bits[1:])))
    if item.body:
        note_lines = []
        for raw_line in item.body.splitlines():
            cleaned = raw_line.strip()
            if cleaned:
                note_lines.append(f"  – {esc(cleaned)}")
        snippet = "\n".join(note_lines)
        if len(snippet) > 240:
            snippet = snippet[:237] + "…"
        line += f"\n{snippet}"
    return line


def _priority_blocks(
    items: list[Item],
    counts: dict[int, tuple[int, int]] | None = None,
) -> list[str]:
    blocks: list[str] = []
    for prio in PRIORITIES:
        group = [item for item in items if item.priority == prio]
        if not group:
            continue
        lines = [f"<b>{prio} · {esc(LABELS[prio])}</b>"]
        for item in group:
            lines.append(task_line(item, subtasks=(counts or {}).get(item.id)))
        blocks.append("\n".join(lines))
    rest = [item for item in items if item.priority not in PRIORITIES]
    if rest:
        lines = ["<b>Weitere</b>"]
        for item in rest:
            lines.append(task_line(item, subtasks=(counts or {}).get(item.id)))
        blocks.append("\n".join(lines))
    return blocks


def grouped_task_list(
    items: list[Item],
    *,
    subtask_counts: dict[int, tuple[int, int]] | None = None,
) -> str:
    if not items:
        return "Keine Aufgaben"
    return "\n\n".join(_priority_blocks(items, subtask_counts))


def draft_summary(
    *,
    title: str,
    body: str | None,
    project_name: str | None,
    priority: str | None,
    subtasks: list[tuple[str, bool]] | None = None,
) -> str:
    lines = [
        "<b>Neue Aufgabe</b>",
        esc(title),
    ]
    if body:
        lines.append(f"<i>{esc(body[:300])}</i>")
    if subtasks:
        preview = " · ".join(item_title for item_title, _ in subtasks[:5])
        extra = f"  +{len(subtasks) - 5}" if len(subtasks) > 5 else ""
        lines.append(esc(preview) + esc(extra))
    if project_name:
        lines.append(esc(project_name))
    if priority:
        lines.append(esc(format_priority(priority)))
    return "\n".join(lines)


def task_card_text(item, project, subtasks: list) -> str:
    prio = format_priority(item.priority) if item.priority else ""
    lines = [
        f"<code>#{item.number}</code>",
        f"<b>{esc(item.title)}</b>",
    ]
    meta = []
    if project:
        meta.append(esc(project.name))
    if prio:
        meta.append(esc(prio))
    if meta:
        lines.append("  ·  ".join(meta))
    if item.body:
        lines.append("")
        lines.append(f"<i>{esc(item.body[:800])}</i>")
    if subtasks:
        done = sum(1 for sub in subtasks if sub.done_at)
        lines.append("")
        lines.append(f"Checkliste  {done}/{len(subtasks)}")
        for sub in subtasks:
            mark = "✓" if sub.done_at else "·"
            lines.append(f"{mark}  {esc(sub.title)}")
        if done == len(subtasks):
            lines.append("")
            lines.append("<i>Alles abgehakt — Erledigt tippen.</i>")
    return "\n".join(lines)


def share_card_plain(item, subtasks: list) -> str:
    """Klartext: nur Titel und Checkliste, fuer Telegrams Share-Picker."""
    lines = [item.title]
    if subtasks:
        lines.append("")
        for sub in subtasks:
            mark = "✓" if sub.done_at else "·"
            lines.append(f"{mark}  {sub.title}")
    return "\n".join(lines)


def share_card_text(item, subtasks: list) -> str:
    """Snapshot zum Teilen: nur Titel und Checkliste."""
    lines = [f"<b>{esc(item.title)}</b>"]
    if subtasks:
        lines.append("")
        for sub in subtasks:
            mark = "✓" if sub.done_at else "·"
            lines.append(f"{mark}  {esc(sub.title)}")
    return "\n".join(lines)
