"""Repository- und Sortier-Tests."""

from __future__ import annotations

import pytest

from taskbuddy.db import TaskRepository


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
