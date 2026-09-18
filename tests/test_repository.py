"""Repository- und Sortier-Tests."""

from __future__ import annotations

import pytest

from taskbuddy.db import Database, TaskRepository


@pytest.mark.asyncio
async def test_default_projects_and_priority_sort(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(1)
        assert [p.key for p in projects[:3]] == ["privat", "arbeit", "backlog"]
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
async def test_priority_filter(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(2)
        privat = projects[0]
        await repo.create_item(
            user_id=2, project_id=privat.id, item_type="task", title="a", priority="A"
        )
        await repo.create_item(
            user_id=2, project_id=privat.id, item_type="task", title="b1", priority="B"
        )
        await repo.create_item(
            user_id=2, project_id=privat.id, item_type="task", title="b2", priority="B"
        )
        page = await repo.list_items(2, item_type="task", priority="B")
        assert {i.title for i in page.items} == {"b1", "b2"}
        assert page.total == 2
        assert all(i.priority == "B" for i in page.items)


@pytest.mark.asyncio
async def test_backlog_cannot_be_deleted(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        await repo.ensure_default_projects(4)
        backlog = await repo.find_project_by_key(4, "backlog")
        assert backlog is not None
        assert await repo.soft_delete_project(4, backlog.id) is None
        still = await repo.find_project_by_key(4, "backlog")
        assert still is not None


@pytest.mark.asyncio
async def test_soft_delete_all_tasks(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(5)
        privat = projects[0]
        await repo.create_item(
            user_id=5, project_id=privat.id, item_type="task", title="one", priority="A"
        )
        await repo.create_item(
            user_id=5, project_id=privat.id, item_type="task", title="two", priority="C"
        )
        removed = await repo.soft_delete_all_tasks(5)
        assert removed == 2
        page = await repo.list_items(5, item_type="task")
        assert page.total == 0
        assert page.items == []


@pytest.mark.asyncio
async def test_list_sorts_project_then_priority_and_hides_backlog(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(6)
        privat, arbeit, backlog = projects[0], projects[1], projects[2]
        await repo.create_item(
            user_id=6, project_id=arbeit.id, item_type="task", title="work-a", priority="A"
        )
        await repo.create_item(
            user_id=6, project_id=privat.id, item_type="task", title="priv-d", priority="D"
        )
        await repo.create_item(
            user_id=6, project_id=privat.id, item_type="task", title="priv-a", priority="A"
        )
        await repo.create_item(
            user_id=6, project_id=backlog.id, item_type="task", title="later", priority="C"
        )
        page = await repo.list_items(6, item_type="task", exclude_kind="backlog")
        assert [i.title for i in page.items] == ["priv-a", "priv-d", "work-a"]
        assert page.total == 3
        backlog_page = await repo.list_items(6, item_type="task", project_id=backlog.id)
        assert [i.title for i in backlog_page.items] == ["later"]


@pytest.mark.asyncio
async def test_soft_delete_all_can_exclude_backlog(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(8)
        privat, backlog = projects[0], projects[2]
        await repo.create_item(
            user_id=8, project_id=privat.id, item_type="task", title="active", priority="A"
        )
        await repo.create_item(
            user_id=8, project_id=backlog.id, item_type="task", title="parked", priority="C"
        )
        removed = await repo.soft_delete_all_tasks(8, exclude_kind="backlog")
        assert removed == 1
        assert (await repo.list_items(8, item_type="task", exclude_kind="backlog")).total == 0
        assert (await repo.list_items(8, item_type="task", project_id=backlog.id)).total == 1


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


@pytest.mark.asyncio
async def test_rename_and_delete_custom_project(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        await repo.ensure_default_projects(9)
        project = await repo.create_project(9, "Sidekick")
        await repo.create_item(
            user_id=9,
            project_id=project.id,
            item_type="task",
            title="x",
            priority="D",
        )
        renamed = await repo.rename_project(9, project.id, "Sidequest")
        assert renamed is not None
        assert renamed.name == "Sidequest"
        assert renamed.key == "sidequest"
        removed = await repo.soft_delete_project(9, project.id)
        assert removed == 1
        assert await repo.get_project(9, project.id) is None
        privat = await repo.find_project_by_key(9, "privat")
        assert privat is not None
        assert await repo.soft_delete_project(9, privat.id) is None


@pytest.mark.asyncio
async def test_update_item_fields(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(13)
        item = await repo.create_item(
            user_id=13,
            project_id=projects[0].id,
            item_type="task",
            title="old",
            body="note",
            priority="C",
        )
        updated = await repo.update_item(
            13, item.id, title="new", body="better", priority="A", project_id=projects[1].id
        )
        assert updated is not None
        assert updated.title == "new"
        assert updated.body == "better"
        assert updated.priority == "A"
        assert updated.project_id == projects[1].id
        cleared = await repo.update_item(13, item.id, body=None)
        assert cleared is not None
        assert cleared.body is None


@pytest.mark.asyncio
async def test_subtasks_toggle_and_counts(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(14)
        item = await repo.create_item(
            user_id=14,
            project_id=projects[0].id,
            item_type="task",
            title="Report",
            priority="B",
        )
        created = await repo.add_subtasks(
            14, item.id, [("Intro", False), ("Charts", True), ("Review", False)]
        )
        assert len(created) == 3
        counts = await repo.subtask_counts(14, [item.id])
        assert counts[item.id] == (1, 3)
        toggled = await repo.toggle_subtask(14, created[0].id)
        assert toggled is not None and toggled.done_at is not None
        counts = await repo.subtask_counts(14, [item.id])
        assert counts[item.id] == (2, 3)
        open_subs = await repo.list_open_subtasks(14)
        assert {s.title for s in open_subs} == {"Review"}


@pytest.mark.asyncio
async def test_restore_soft_deleted_task(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(15)
        item = await repo.create_item(
            user_id=15,
            project_id=projects[0].id,
            item_type="task",
            title="oops",
            priority="A",
        )
        await repo.soft_delete_item(15, item.id)
        assert await repo.get_item(15, item.id) is None
        deleted = await repo.list_deleted_tasks(15, limit=1)
        assert deleted and deleted[0].id == item.id
        restored = await repo.restore_item(15, item.id)
        assert restored is not None
        assert restored.deleted_at is None
        assert restored.number == item.number
        assert (await repo.get_item(15, item.id)).title == "oops"


@pytest.mark.asyncio
async def test_task_numbers_reuse_lowest_gap(db):
    async with db.session() as session:
        repo = TaskRepository(session)
        projects = await repo.ensure_default_projects(20)
        privat = projects[0]
        first = await repo.create_item(
            user_id=20, project_id=privat.id, item_type="task", title="one", priority="A"
        )
        second = await repo.create_item(
            user_id=20, project_id=privat.id, item_type="task", title="two", priority="B"
        )
        third = await repo.create_item(
            user_id=20, project_id=privat.id, item_type="task", title="three", priority="C"
        )
        assert [first.number, second.number, third.number] == [1, 2, 3]

        await repo.soft_delete_item(20, first.id)
        reused = await repo.create_item(
            user_id=20, project_id=privat.id, item_type="task", title="new", priority="A"
        )
        assert reused.number == 1
        assert reused.id != first.id
        found = await repo.get_item_by_number(20, 1)
        assert found is not None and found.id == reused.id

        restored = await repo.restore_item(20, first.id)
        assert restored is not None
        assert restored.number == 4

        other = await repo.ensure_default_projects(21)
        isolated = await repo.create_item(
            user_id=21,
            project_id=other[0].id,
            item_type="task",
            title="solo",
            priority="A",
        )
        assert isolated.number == 1


@pytest.mark.asyncio
async def test_legacy_items_keep_id_as_number_and_reuse_gaps(tmp_path):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    url = f"sqlite+aiosqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE projects (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    key VARCHAR(64) NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    kind VARCHAR(16) NOT NULL DEFAULT 'custom',
                    created_at DATETIME,
                    deleted_at DATETIME
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    type VARCHAR(16) NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT,
                    priority VARCHAR(1),
                    created_at DATETIME,
                    updated_at DATETIME,
                    deleted_at DATETIME
                )
                """
            )
        )
        await conn.execute(
            text(
                "INSERT INTO projects (id, user_id, key, name, kind) "
                "VALUES (1, 1, 'privat', 'Privat', 'private')"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO items (id, user_id, project_id, type, title, priority) "
                "VALUES (7, 1, 1, 'task', 'old', 'A')"
            )
        )
    await engine.dispose()

    database = Database(url)
    await database.create_schema()
    try:
        async with database.session() as session:
            repo = TaskRepository(session)
            old = await repo.get_item(1, 7)
            assert old is not None
            assert old.number == 7
            created = await repo.create_item(
                user_id=1,
                project_id=1,
                item_type="task",
                title="fresh",
                priority="B",
            )
            assert created.number == 1
    finally:
        await database.dispose()
