"""Repository- und Sortier-Tests."""

from __future__ import annotations

import pytest

from taskbuddy.db import TaskRepository


@pytest.mark.asyncio
async def test_default_projects_and_priority_sort(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(1)
        assert [p.key for p in projects[:2]] == ["privat", "arbeit"]
        privat = projects[0]
        await repo.create_item(
            user_id=1, project_id=privat.id, item_type="task", title="low", priority="D"
        )
        await repo.create_item(
            user_id=1, project_id=privat.id, item_type="task", title="hot", priority="A"
        )
        await repo.create_item(
            user_id=1, project_id=privat.id, item_type="task", title="mid", priority="C"
        )
        page = await repo.list_items(1, item_type="task")
        assert [i.title for i in page.items] == ["hot", "mid", "low"]


@pytest.mark.asyncio
async def test_note_has_no_priority(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(7)
        note = await repo.create_item(
            user_id=7,
            project_id=projects[0].id,
            item_type="note",
            title="Idee",
            body="spaeter",
            priority="A",
        )
        assert note.priority is None


@pytest.mark.asyncio
async def test_done_soft_deletes(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(3)
        item = await repo.create_item(
            user_id=3,
            project_id=projects[1].id,
            item_type="task",
            title="fertig",
            priority="B",
        )
        deleted = await repo.soft_delete_item(3, item.id)
        assert deleted is not None
        assert await repo.get_item(3, item.id) is None
