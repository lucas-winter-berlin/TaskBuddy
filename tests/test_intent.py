"""Intent- und Checklisten-Tests."""

from types import SimpleNamespace

from taskbuddy.services.intent import (
    match_by_title,
    parse_item_id,
    parse_text_intent,
    split_notes_and_subtasks,
)


def test_parse_done_and_edit_intents():
    done = parse_text_intent("erledigt Steuererklärung")
    assert done is not None and done.kind == "done"
    assert done.query == "Steuererklärung"
    edit = parse_text_intent("bearbeiten Quartalsbericht")
    assert edit is not None and edit.kind == "edit"
    assert parse_text_intent("Neue Aufgabe") is None
    assert parse_text_intent("done #12").query == "#12"
    opened = parse_text_intent("#12")
    assert opened is not None and opened.kind == "edit" and opened.query == "#12"
    assert parse_text_intent("show 12") is None
    assert parse_text_intent("12") is None
    undo = parse_text_intent("undo")
    assert undo is not None and undo.kind == "undo" and undo.query == ""
    assert parse_text_intent("undo 12").query == "12"
    assert parse_text_intent("restore #12").query == "#12"


def test_parse_item_id():
    assert parse_item_id("12") == 12
    assert parse_item_id("#12") == 12
    assert parse_item_id("Steuer") is None
    assert parse_item_id("12 later") is None


def test_match_exact_wins_over_substring():
    items = [
        SimpleNamespace(id=1, title="Steuer"),
        SimpleNamespace(id=2, title="Steuererklärung vorbereiten"),
    ]
    assert [i.id for i in match_by_title(items, "steuer")] == [1]


def test_match_substring_ambiguous():
    items = [
        SimpleNamespace(id=1, title="Kundenanruf zurückrufen"),
        SimpleNamespace(id=2, title="Kundenmail schreiben"),
    ]
    assert [i.id for i in match_by_title(items, "kunde")] == [1, 2]


def test_match_substring_unique_and_too_short():
    items = [SimpleNamespace(id=1, title="Quartalsbericht schreiben")]
    assert [i.id for i in match_by_title(items, "quartal")] == [1]
    assert match_by_title(items, "ab") == []


def test_split_notes_and_subtasks():
    notes, subs = split_notes_and_subtasks(
        "Zahlen von Q3, bitte an Anna\n- Intro\n* Charts\n[ ] Review\n[x] Done already"
    )
    assert notes == "Zahlen von Q3, bitte an Anna"
    assert subs == [
        ("Intro", False),
        ("Charts", False),
        ("Review", False),
        ("Done already", True),
    ]
