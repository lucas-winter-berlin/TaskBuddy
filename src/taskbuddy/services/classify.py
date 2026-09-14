"""Erkennung von Item-Typ und Projekt."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..db.models import Project

_TASK_PREFIX = re.compile(
    r"^\s*(?:task|aufgabe|todo)\s*[:\-–]\s*",
    re.IGNORECASE,
)
_PRIVATE = re.compile(
    r"\b(privat|private|zuhause|familie|personal|pers[oö]nlich)\b",
    re.IGNORECASE,
)
_WORK = re.compile(
    r"\b(arbeit|job|büro|buero|kunde|meeting|standup|office|work|beruflich)\b",
    re.IGNORECASE,
)
_BACKLOG = re.compile(
    r"\b(backlog|aufwendig|aufwändig|grosse sache|große sache|"
    r"wenn ruhe|ruhige phase|lebensphase|nicht schnell)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedInput:
    item_type: str  # immer task
    title: str
    body: str | None
    forced_type: bool


@dataclass(frozen=True)
class ProjectGuess:
    project_id: int | None
    confidence: float
    reason: str


def parse_input(text: str, *, default_type: str = "task") -> ParsedInput:
    raw = text.strip()
    forced = False
    item_type = default_type or "task"
    if _TASK_PREFIX.match(raw):
        item_type = "task"
        forced = True
        raw = _TASK_PREFIX.sub("", raw, count=1).strip()

    if "\n" in raw:
        title, _, rest = raw.partition("\n")
        body = rest.strip() or None
    else:
        title, body = raw, None
    return ParsedInput(
        item_type=item_type or "task",
        title=title.strip(),
        body=body,
        forced_type=forced,
    )


def guess_project(text: str, projects: list[Project]) -> ProjectGuess:
    """Match gegen Keywords und Projektnamen."""
    if not projects:
        return ProjectGuess(None, 0.0, "keine Projekte")

    lowered = text.lower()
    # Explizite Projektnamen (laengere zuerst)
    named = sorted(projects, key=lambda p: len(p.name), reverse=True)
    for project in named:
        name = project.name.lower()
        key = project.key.lower()
        if len(name) >= 3 and re.search(rf"\b{re.escape(name)}\b", lowered):
            return ProjectGuess(project.id, 0.9, f"Name „{project.name}“")
        if len(key) >= 3 and re.search(rf"\b{re.escape(key)}\b", lowered):
            return ProjectGuess(project.id, 0.85, f"Key „{project.key}“")

    private = next((p for p in projects if p.kind == "private"), None)
    work = next((p for p in projects if p.kind == "work"), None)
    backlog = next((p for p in projects if p.kind == "backlog"), None)

    if private and _PRIVATE.search(text):
        return ProjectGuess(private.id, 0.8, "Privat-Keyword")
    if work and _WORK.search(text):
        return ProjectGuess(work.id, 0.8, "Arbeit-Keyword")
    if backlog and _BACKLOG.search(text):
        return ProjectGuess(backlog.id, 0.8, "Backlog-Keyword")

    return ProjectGuess(None, 0.2, "unklar")
