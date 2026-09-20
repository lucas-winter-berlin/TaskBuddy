"""Teilen: Tokens, Snapshot-Text, Suche und Kopie."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from taskbuddy.bot import copy as txt
from taskbuddy.bot import keyboards
from taskbuddy.db import TaskRepository
from taskbuddy.services.formatting import share_card_plain, share_card_text
from taskbuddy.services.share import (
    claim_payload,
    claim_url,
    parse_claim_payload,
    telegram_share_url,
)

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
        title="Party vorbereiten",
        body="Unterlagen im Ordner",
        priority="A",
    )
    subtasks = [
        SimpleNamespace(title="Alkohol abholen", done_at=datetime.now(timezone.utc)),
        SimpleNamespace(title="Pizza vorbestellen", done_at=None),
    ]
    text = share_card_text(item, subtasks)
    assert text.startswith("<b>Party vorbereiten</b>")
    assert "#12" not in text
    assert "Aufgabe von" not in text
    assert "Arbeit" not in text
    assert "Privat" not in text
    assert "Unterlagen" not in text
    assert "t.me" not in text
    assert "✓  Alkohol abholen" in text
    assert "·  Pizza vorbestellen" in text
    plain = share_card_plain(item, subtasks)
    assert plain.startswith("Party vorbereiten")
    assert "<" not in plain
    assert "#12" not in plain
    assert "Aufgabe von" not in plain


def test_share_and_claim_keyboards():
    markup = keyboards.edit_task_keyboard(7, [], number=12)
    data = [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    ]
    assert "shr:go:7" in data

    claim = keyboards.claim_keyboard("taskbuddy_bot", "claim_7_abcabcabca")
    urls = [button.url for row in claim.inline_keyboard for button in row]
    assert urls == ["https://t.me/taskbuddy_bot?start=claim_7_abcabcabca"]
    labels = [button.text for row in claim.inline_keyboard for button in row]
    assert any(txt.BTN_CLAIM in (label or "") for label in labels)

    share = keyboards.share_send_keyboard("https://t.me/share/url?url=x&text=y")
    share_urls = [button.url for row in share.inline_keyboard for button in row]
    assert share_urls == ["https://t.me/share/url?url=x&text=y"]


def test_telegram_share_url_encodes_text():
    url = telegram_share_url(text="Party vorbereiten\n·  Pizza vorbestellen")
    assert url.startswith("https://t.me/share/url?")
    assert "text=" in url
    assert "url=" not in url
    assert " " not in url
    assert len(url) <= 2048
    with_link = telegram_share_url(
        url="https://t.me/bot?start=claim_1",
        text="Party vorbereiten",
    )
    assert "url=" in with_link
    assert claim_url("BaxxTaskBuddyBot", "claim_1_abc") == (
        "https://t.me/BaxxTaskBuddyBot?start=claim_1_abc"
    )


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
        by_id = await repo.find_share_tasks(30, f"i:{first.id}")
        assert [item.id for item in by_id] == [first.id]
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
