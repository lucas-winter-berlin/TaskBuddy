"""Heuristik-Tests."""

from __future__ import annotations

from taskbuddy.db.models import Project
from taskbuddy.services.classify import guess_project, parse_input
from taskbuddy.services.priority import format_priority, guess_priority


def test_parse_note_prefix():
    parsed = parse_input("note: get milk")
    assert parsed.item_type == "note"
    assert parsed.title == "get milk"


def test_parse_task_default():
    parsed = parse_input("Steuern einreichen")
    assert parsed.item_type == "task"
    assert parsed.title == "Steuern einreichen"


def test_guess_priority_urgent_important():
    g = guess_priority("wichtig und dringend: Server down")
    assert g.priority == "A"
    assert g.confidence >= 0.7


def test_guess_project_work_keyword():
    projects = [
        Project(id=1, user_id=1, key="privat", name="Privat", kind="private"),
        Project(id=2, user_id=1, key="arbeit", name="Arbeit", kind="work"),
    ]
    g = guess_project("Meeting mit Kunde vorbereiten", projects)
    assert g.project_id == 2


def test_format_priority():
    assert "Wichtig" in format_priority("A")
