"""HTML-Formatierung fuer Telegram-Antworten."""

from __future__ import annotations

import html

from .. import icons as ic
from ..db.models import Item, Project
from .priority import format_priority


def esc(value: str | None) -> str:
    return html.escape(value or "")


def project_line(project: Project) -> str:
    return f"{ic.html('section')} <b>{esc(project.name)}</b> <code>{esc(project.key)}</code>"


def item_line(item: Item, project: Project | None = None) -> str:
    if item.type == "task":
        head = f"<b>[{esc(item.priority)}]</b> {esc(item.title)}"
        meta = format_priority(item.priority)
    else:
        head = f"{ic.html('note')} {esc(item.title)}"
        meta = "Notiz"
    bits = [f"<code>#{item.id}</code>", head]
    if project is not None:
        bits.append(f"· {esc(project.name)}")
    line = " ".join(bits)
    if item.body:
        line += f"\n<i>{esc(item.body[:200])}</i>"
    if meta and item.type == "task":
        line += f"\n{esc(meta)}"
    return line


def draft_summary(
    *,
    item_type: str,
    title: str,
    body: str | None,
    project_name: str | None,
    priority: str | None,
) -> str:
    kind = "Aufgabe" if item_type == "task" else "Notiz"
    lines = [
        f"{ic.html('save')} <b>Neue {kind}</b>",
        esc(title),
    ]
    if body:
        lines.append(f"<i>{esc(body[:300])}</i>")
    if project_name:
        lines.append(f"Projekt: <b>{esc(project_name)}</b>")
    else:
        lines.append("Projekt: <i>noch wählen</i>")
    if item_type == "task":
        if priority:
            lines.append(f"Priorität: <b>{esc(format_priority(priority))}</b>")
        else:
            lines.append("Priorität: <i>noch wählen</i>")
    return "\n".join(lines)
