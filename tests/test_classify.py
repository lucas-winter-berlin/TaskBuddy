"""Heuristik-Tests."""

from __future__ import annotations

from taskbuddy.bot.handlers.query import parse_tasks_args
from taskbuddy.db.models import Project
from taskbuddy.services.classify import guess_project, parse_input
from taskbuddy.services.formatting import grouped_task_list, task_line
from taskbuddy.services.priority import format_priority, guess_priority


def test_parse_note_prefix_is_a_normal_task():
    parsed = parse_input("note: get milk")
    assert parsed.item_type == "task"
    assert parsed.title == "note: get milk"


def test_parse_task_default():
    parsed = parse_input("Steuern einreichen")
    assert parsed.item_type == "task"
    assert parsed.title == "Steuern einreichen"


def test_parse_task_prefix():
    parsed = parse_input("todo: Milch kaufen")
    assert parsed.item_type == "task"
    assert parsed.title == "Milch kaufen"
    assert parsed.forced_type is True


def test_guess_priority_urgent_important():
    g = guess_priority("wichtig und dringend: Server down")
    assert g.priority == "A"
    assert g.confidence >= 0.7


def test_guess_project_work_keyword():
    projects = [
        Project(id=1, user_id=1, key="privat", name="Privat", kind="private"),
        Project(id=2, user_id=1, key="arbeit", name="Arbeit", kind="work"),
        Project(id=3, user_id=1, key="backlog", name="Backlog", kind="backlog"),
    ]
    g = guess_project("Meeting mit Kunde vorbereiten", projects)
    assert g.project_id == 2


def test_guess_project_backlog_keyword():
    projects = [
        Project(id=1, user_id=1, key="privat", name="Privat", kind="private"),
        Project(id=2, user_id=1, key="arbeit", name="Arbeit", kind="work"),
        Project(id=3, user_id=1, key="backlog", name="Backlog", kind="backlog"),
    ]
    g = guess_project("aufwendig: Website neu aufsetzen wenn ruhe", projects)
    assert g.project_id == 3


def test_format_priority():
    assert "Wichtig" in format_priority("A")


def test_parse_tasks_args_priority_and_project():
    assert parse_tasks_args(["A"]) == ("A", None)
    assert parse_tasks_args(["Arbeit"]) == (None, "Arbeit")
    assert parse_tasks_args(["A", "Privat"]) == ("A", "Privat")
    assert parse_tasks_args(["Backlog", "C"]) == ("C", "Backlog")


def test_grouped_task_list_has_section_headers_once():
    class _Item:
        def __init__(self, item_id, title, priority, project_id, body=None):
            self.id = item_id
            self.number = item_id
            self.title = title
            self.priority = priority
            self.project_id = project_id
            self.body = body

    items = [
        _Item(1, "Hot", "A", 1),
        _Item(2, "Also hot", "A", 1),
        _Item(3, "Later", "C", 2),
    ]
    text = grouped_task_list(items)
    assert "<b>3 Aufgaben</b>" not in text
    assert "<b>Privat</b>" not in text
    assert "<b>Arbeit</b>" not in text
    assert text.count("<b>A ·") == 1
    assert text.count("<b>C ·") == 1
    assert "Wichtig &amp; Dringend" in text
    assert "[A]" not in text
    assert "#1" in text and "Hot" in text
    assert "· Privat" not in text
    assert "· Arbeit" not in text
    line = task_line(items[0], subtasks=(2, 3))
    assert "2/3" in line
    noted = task_line(
        _Item(9, "Report", "A", 1, body="Zahlen von Q3\nbitte an Anna")
    )
    assert "  – Zahlen von Q3" in noted
    assert "  – bitte an Anna" in noted
