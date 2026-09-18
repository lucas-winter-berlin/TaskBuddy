"""Datenzugriff fuer Projekte und Items."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Item, Project, Subtask, utcnow

PRIORITY_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
BUILTIN_KINDS = ("private", "work", "backlog")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    base = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return (base or "projekt")[:64]


@dataclass
class Page:
    items: list
    total: int
    offset: int
    limit: int

    @property
    def has_prev(self) -> bool:
        return self.offset > 0

    @property
    def has_next(self) -> bool:
        return self.offset + self.limit < self.total


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_default_projects(self, user_id: int) -> list[Project]:
        """Legt Privat, Arbeit und Backlog an, falls noch nicht vorhanden."""
        existing = await self.list_projects(user_id)
        by_key = {p.key: p for p in existing}
        seeds = [
            ("privat", "Privat", "private"),
            ("arbeit", "Arbeit", "work"),
            ("backlog", "Backlog", "backlog"),
        ]
        created = False
        for key, name, kind in seeds:
            if key in by_key:
                continue
            self.session.add(Project(user_id=user_id, key=key, name=name, kind=kind))
            created = True
        if created:
            await self.session.flush()
        return await self.list_projects(user_id)

    async def list_projects(self, user_id: int) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.user_id == user_id, Project.deleted_at.is_(None))
            .order_by(
                case(
                    (Project.kind == "private", 0),
                    (Project.kind == "work", 1),
                    (Project.kind == "backlog", 2),
                    else_=3,
                ),
                Project.name.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_project(self, user_id: int, project_id: int) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_project_by_key(self, user_id: int, key: str) -> Project | None:
        stmt = select(Project).where(
            Project.user_id == user_id,
            Project.key == key,
            Project.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_project_by_name(self, user_id: int, name: str) -> Project | None:
        lowered = name.strip().lower()
        projects = await self.list_projects(user_id)
        for project in projects:
            if project.name.lower() == lowered or project.key == slugify(name):
                return project
        return None

    async def create_project(self, user_id: int, name: str) -> Project:
        base = slugify(name)
        key = base
        suffix = 2
        while await self.find_project_by_key(user_id, key) is not None:
            key = f"{base}-{suffix}"[:64]
            suffix += 1
        project = Project(user_id=user_id, key=key, name=name.strip(), kind="custom")
        self.session.add(project)
        await self.session.flush()
        return project

    async def rename_project(
        self, user_id: int, project_id: int, new_name: str
    ) -> Project | None:
        project = await self.get_project(user_id, project_id)
        if project is None:
            return None
        name = new_name.strip()
        if not name:
            raise ValueError("Empty project name")
        clash = await self.find_project_by_name(user_id, name)
        if clash is not None and clash.id != project.id:
            raise ValueError(f"Name already taken: {clash.name}")
        project.name = name
        # Key nur bei Custom-Projekten anpassen; Defaults behalten stabile Keys.
        if project.kind == "custom":
            base = slugify(name)
            key = base
            suffix = 2
            while True:
                existing = await self.find_project_by_key(user_id, key)
                if existing is None or existing.id == project.id:
                    break
                key = f"{base}-{suffix}"[:64]
                suffix += 1
            project.key = key
        await self.session.flush()
        return project

    async def soft_delete_project(self, user_id: int, project_id: int) -> int | None:
        """Soft-Delete Custom-Projekt inkl. aller offenen Items. Liefert Anzahl Items."""
        project = await self.get_project(user_id, project_id)
        if project is None or project.kind in BUILTIN_KINDS:
            return None
        now = utcnow()
        page = await self.list_items(user_id, project_id=project_id, limit=10_000)
        for item in page.items:
            item.deleted_at = now
        project.deleted_at = now
        await self.session.flush()
        return len(page.items)

    def _lowest_free_number(self, used: set[int]) -> int:
        number = 1
        while number in used:
            number += 1
        return number

    async def _open_numbers(self, user_id: int) -> set[int]:
        stmt = select(Item.number).where(
            Item.user_id == user_id,
            Item.deleted_at.is_(None),
            Item.number.isnot(None),
        )
        result = await self.session.execute(stmt)
        return {int(value) for value in result.scalars().all()}

    async def _next_open_number(self, user_id: int) -> int:
        return self._lowest_free_number(await self._open_numbers(user_id))

    async def create_item(
        self,
        *,
        user_id: int,
        project_id: int,
        item_type: str,
        title: str,
        body: str | None = None,
        priority: str | None = None,
    ) -> Item:
        if item_type == "task":
            if priority not in PRIORITY_ORDER:
                raise ValueError(f"Invalid priority: {priority!r}")
        else:
            priority = None
        item = Item(
            user_id=user_id,
            project_id=project_id,
            type=item_type,
            title=title.strip(),
            body=(body.strip() if body else None) or None,
            number=await self._next_open_number(user_id),
            priority=priority,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_item(
        self,
        user_id: int,
        item_id: int,
        *,
        title: str | None = None,
        body: str | None = ...,
        priority: str | None = None,
        project_id: int | None = None,
    ) -> Item | None:
        item = await self.get_item(user_id, item_id)
        if item is None:
            return None
        if title is not None:
            cleaned = title.strip()
            if not cleaned:
                raise ValueError("Empty title")
            item.title = cleaned
        if body is not ...:
            item.body = (body.strip() if body else None) or None
        if priority is not None:
            if item.type == "task" and priority not in PRIORITY_ORDER:
                raise ValueError(f"Invalid priority: {priority!r}")
            item.priority = priority
        if project_id is not None:
            project = await self.get_project(user_id, project_id)
            if project is None:
                raise ValueError("Project not found")
            item.project_id = project_id
        item.updated_at = utcnow()
        await self.session.flush()
        return item

    async def list_open_tasks(self, user_id: int, *, limit: int = 500) -> list[Item]:
        page = await self.list_items(user_id, item_type="task", limit=limit)
        return page.items

    async def get_item(
        self, user_id: int, item_id: int, *, include_deleted: bool = False
    ) -> Item | None:
        filters = [Item.id == item_id, Item.user_id == user_id]
        if not include_deleted:
            filters.append(Item.deleted_at.is_(None))
        stmt = select(Item).where(*filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_item_by_number(
        self, user_id: int, number: int, *, include_deleted: bool = False
    ) -> Item | None:
        filters = [Item.user_id == user_id, Item.number == number]
        if not include_deleted:
            filters.append(Item.deleted_at.is_(None))
        stmt = select(Item).where(*filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_deleted_item_by_number(self, user_id: int, number: int) -> Item | None:
        stmt = (
            select(Item)
            .where(
                Item.user_id == user_id,
                Item.number == number,
                Item.type == "task",
                Item.deleted_at.isnot(None),
            )
            .order_by(Item.deleted_at.desc(), Item.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def restore_item(self, user_id: int, item_id: int) -> Item | None:
        item = await self.get_item(user_id, item_id, include_deleted=True)
        if item is None or item.deleted_at is None:
            return None
        used = await self._open_numbers(user_id)
        if item.number in used:
            item.number = self._lowest_free_number(used)
        item.deleted_at = None
        item.updated_at = utcnow()
        await self.session.flush()
        return item

    async def list_deleted_tasks(self, user_id: int, *, limit: int = 50) -> list[Item]:
        stmt = (
            select(Item)
            .where(
                Item.user_id == user_id,
                Item.type == "task",
                Item.deleted_at.isnot(None),
            )
            .order_by(Item.deleted_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete_item(self, user_id: int, item_id: int) -> Item | None:
        item = await self.get_item(user_id, item_id)
        if item is None:
            return None
        item.deleted_at = utcnow()
        await self.session.flush()
        return item

    def _project_kind_sort(self):
        return case(
            (Project.kind == "private", 0),
            (Project.kind == "work", 1),
            (Project.kind == "backlog", 2),
            else_=3,
        )

    async def soft_delete_all_tasks(
        self,
        user_id: int,
        *,
        project_id: int | None = None,
        exclude_kind: str | None = None,
    ) -> int:
        """Soft-delete offener Tasks, optional nach Projekt/Kind gefiltert."""
        filters = [
            Item.user_id == user_id,
            Item.type == "task",
            Item.deleted_at.is_(None),
        ]
        stmt = select(Item)
        if project_id is not None:
            filters.append(Item.project_id == project_id)
        if exclude_kind is not None:
            stmt = stmt.join(Project, Item.project_id == Project.id)
            filters.append(Project.kind != exclude_kind)
            filters.append(Project.deleted_at.is_(None))
        result = await self.session.execute(stmt.where(*filters))
        items = list(result.scalars().all())
        now = utcnow()
        for item in items:
            item.deleted_at = now
        await self.session.flush()
        return len(items)

    def _priority_sort(self):
        return case(
            (Item.priority == "A", 0),
            (Item.priority == "B", 1),
            (Item.priority == "C", 2),
            (Item.priority == "D", 3),
            else_=9,
        )

    async def list_items(
        self,
        user_id: int,
        *,
        item_type: str | None = None,
        project_id: int | None = None,
        priority: str | None = None,
        exclude_kind: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Page:
        filters = [
            Item.user_id == user_id,
            Item.deleted_at.is_(None),
            Project.deleted_at.is_(None),
        ]
        if item_type:
            filters.append(Item.type == item_type)
        if project_id is not None:
            filters.append(Item.project_id == project_id)
        if priority is not None:
            filters.append(Item.priority == priority)
        if exclude_kind is not None:
            filters.append(Project.kind != exclude_kind)

        count_stmt = (
            select(func.count())
            .select_from(Item)
            .join(Project, Item.project_id == Project.id)
            .where(*filters)
        )
        total = int((await self.session.execute(count_stmt)).scalar_one())

        stmt: Select = (
            select(Item)
            .join(Project, Item.project_id == Project.id)
            .where(*filters)
            .order_by(
                self._project_kind_sort(),
                Project.name.asc(),
                self._priority_sort(),
                Item.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return Page(
            items=list(result.scalars().all()),
            total=total,
            offset=offset,
            limit=limit,
        )

    async def search_items(
        self,
        user_id: int,
        query: str,
        *,
        item_type: str | None = None,
        limit: int = 20,
    ) -> list[Item]:
        q = f"%{query.strip().lower()}%"
        filters = [
            Item.user_id == user_id,
            Item.deleted_at.is_(None),
            or_(func.lower(Item.title).like(q), func.lower(Item.body).like(q)),
        ]
        if item_type:
            filters.append(Item.type == item_type)
        stmt = (
            select(Item)
            .join(Project, Item.project_id == Project.id)
            .where(*filters, Project.deleted_at.is_(None))
            .order_by(
                self._project_kind_sort(),
                Project.name.asc(),
                self._priority_sort(),
                Item.created_at.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_subtasks(self, user_id: int, item_id: int) -> list[Subtask]:
        stmt = (
            select(Subtask)
            .where(
                Subtask.user_id == user_id,
                Subtask.item_id == item_id,
                Subtask.deleted_at.is_(None),
            )
            .order_by(Subtask.position.asc(), Subtask.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_subtasks(
        self,
        user_id: int,
        item_id: int,
        entries: list[tuple[str, bool]],
    ) -> list[Subtask]:
        existing = await self.list_subtasks(user_id, item_id)
        position = (existing[-1].position + 1) if existing else 0
        created: list[Subtask] = []
        now = utcnow()
        for title, done in entries:
            cleaned = title.strip()
            if not cleaned:
                continue
            row = Subtask(
                user_id=user_id,
                item_id=item_id,
                title=cleaned,
                position=position,
                done_at=now if done else None,
            )
            self.session.add(row)
            created.append(row)
            position += 1
        if created:
            await self.session.flush()
        return created

    async def toggle_subtask(self, user_id: int, subtask_id: int) -> Subtask | None:
        stmt = select(Subtask).where(
            Subtask.id == subtask_id,
            Subtask.user_id == user_id,
            Subtask.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        parent = await self.get_item(user_id, row.item_id)
        if parent is None:
            return None
        row.done_at = None if row.done_at else utcnow()
        await self.session.flush()
        return row

    async def subtask_counts(
        self, user_id: int, item_ids: list[int]
    ) -> dict[int, tuple[int, int]]:
        if not item_ids:
            return {}
        stmt = select(Subtask).where(
            Subtask.user_id == user_id,
            Subtask.item_id.in_(item_ids),
            Subtask.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        totals: dict[int, list[int]] = {}
        for row in result.scalars().all():
            pair = totals.setdefault(row.item_id, [0, 0])
            pair[1] += 1
            if row.done_at is not None:
                pair[0] += 1
        return {item_id: (done, total) for item_id, (done, total) in totals.items() if total}

    async def list_open_subtasks(self, user_id: int, *, limit: int = 500) -> list[Subtask]:
        stmt = (
            select(Subtask)
            .join(Item, Subtask.item_id == Item.id)
            .where(
                Subtask.user_id == user_id,
                Subtask.deleted_at.is_(None),
                Subtask.done_at.is_(None),
                Item.deleted_at.is_(None),
                Item.type == "task",
            )
            .order_by(Subtask.id.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
