"""Teilen: Tokens, Snapshot-Text, Suche und Kopie."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from taskbuddy.bot import copy as txt
from taskbuddy.bot import keyboards
from taskbuddy.db import TaskRepository
from taskbuddy.services.formatting import share_card_text
from taskbuddy.services.share import claim_payload, parse_claim_payload

SECRET = "test-bot-token"


def test_claim_payload_roundtrip_and_tamper():
    payload = claim_payload(42, SECRET)
    assert parse_claim_payload(payload, SECRET) == 42
    assert parse_claim_payload(payload, "other") is None
    last = "1" if payload[-1] != "1" else "2"
    assert parse_claim_payload(payload[:-1] + last, SECRET) is None
    assert parse_claim_payload("claim_42", SECRET) is None
    assert parse_claim_payload("claim_abc_deadbeef12", SECRET) is None


def test_share_card_text_snapshot():
    item = SimpleNamespace(
        number=12,
        title="Steuererklärung",
        body="Unterlagen im Ordner\nZweite Zeile",
        priority="A",
    )
    project = SimpleNamespace(name="Arbeit")
    subtasks = [
        SimpleNamespace(title="Sammeln", done_at=datetime.now(timezone.utc)),
        SimpleNamespace(title="Abschicken", done_at=None),
    ]
    text = share_card_text(item, project, subtasks, from_name="Baxx")
    assert "Aufgabe von Baxx" in text
    assert "#12" in text
    assert "Steuererklärung" in text
    assert "Arbeit" in text
    assert "– Unterlagen im Ordner" in text
    assert "✓  Sammeln" in text
    assert "·  Abschicken" in text
    assert "In TaskBuddy" not in text


def test_share_and_claim_keyboards():
    markup = keyboards.edit_task_keyboard(7, [], number=12)
    queries = [
        button.switch_inline_query
        for row in markup.inline_keyboard
        for button in row
        if button.switch_inline_query is not None
    ]
    assert "#12" in queries

    claim = keyboards.claim_keyboard("taskbuddy_bot", "claim_7_abcabcabca")
    urls = [button.url for row in claim.inline_keyboard for button in row]
    assert urls == ["https://t.me/taskbuddy_bot?start=claim_7_abcabcabca"]
    labels = [button.text for row in claim.inline_keyboard for button in row]
    assert any(txt.BTN_CLAIM in (label or "") for label in labels)


@pytest.mark.asyncio
async def test_find_share_tasks_number_search_and_empty(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(30)
        privat = projects[0]
        first = await repo.create_item(
            user_id=30,
            project_id=privat.id,
            item_type="task",
            title="Milch kaufen",
            priority="B",
        )
        await repo.create_item(
            user_id=30,
            project_id=privat.id,
            item_type="task",
            title="Steuer",
            body="Ordner",
            priority="A",
        )
        by_number = await repo.find_share_tasks(30, f"#{first.number}")
        assert [item.id for item in by_number] == [first.id]
        by_text = await repo.find_share_tasks(30, "steuer")
        assert [item.title for item in by_text] == ["Steuer"]
        listed = await repo.find_share_tasks(30, "")
        assert {item.title for item in listed} == {"Milch kaufen", "Steuer"}
        missing = await repo.find_share_tasks(30, "#999")
        assert missing == []


@pytest.mark.asyncio
async def test_copy_task_to_user_includes_subtasks(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        owner_projects = await repo.ensure_default_projects(31)
        arbeit = next(p for p in owner_projects if p.key == "arbeit")
        source = await repo.create_item(
            user_id=31,
            project_id=arbeit.id,
            item_type="task",
            title="Bericht",
            body="Q3",
            priority="A",
        )
        await repo.add_subtasks(31, source.id, [("Intro", True), ("Charts", False)])

        copied = await repo.copy_task_to_user(source, 32)
        assert copied.user_id == 32
        assert copied.title == "Bericht"
        assert copied.body == "Q3"
        assert copied.priority == "A"
        privat = await repo.find_project_by_key(32, "privat")
        assert privat is not None
        assert copied.project_id == privat.id
        assert copied.number == 1
        subs = await repo.list_subtasks(32, copied.id)
        assert [(s.title, s.done_at is not None) for s in subs] == [
            ("Intro", True),
            ("Charts", False),
        ]
        original = await repo.get_item(31, source.id)
        assert original is not None
        assert original.deleted_at is None
