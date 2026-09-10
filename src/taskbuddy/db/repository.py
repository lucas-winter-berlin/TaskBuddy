"""Datenzugriff fuer Projekte und Items."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Item, Project, utcnow

PRIORITY_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}

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
        """Legt Privat und Arbeit an, falls noch nicht vorhanden."""
        existing = await self.list_projects(user_id)
        by_key = {p.key: p for p in existing}
        seeds = [
            ("privat", "Privat", "private"),
            ("arbeit", "Arbeit", "work"),
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
                    else_=2,
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

    async def soft_delete_project(self, user_id: int, project_id: int) -> bool:
        project = await self.get_project(user_id, project_id)
        if project is None or project.kind in ("private", "work"):
            return False
        project.deleted_at = utcnow()
        await self.session.flush()
        return True

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
                raise ValueError(f"Ungueltige Prioritaet: {priority!r}")
        else:
            priority = None
        item = Item(
            user_id=user_id,
            project_id=project_id,
            type=item_type,
            title=title.strip(),
            body=(body.strip() if body else None) or None,
            priority=priority,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_item(self, user_id: int, item_id: int) -> Item | None:
        stmt = select(Item).where(
            Item.id == item_id,
            Item.user_id == user_id,
            Item.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete_item(self, user_id: int, item_id: int) -> Item | None:
        item = await self.get_item(user_id, item_id)
        if item is None:
            return None
        item.deleted_at = utcnow()
        await self.session.flush()
        return item

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
        offset: int = 0,
        limit: int = 20,
    ) -> Page:
        filters = [Item.user_id == user_id, Item.deleted_at.is_(None)]
        if item_type:
            filters.append(Item.type == item_type)
        if project_id is not None:
            filters.append(Item.project_id == project_id)

        count_stmt = select(func.count()).select_from(Item).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        stmt: Select = (
            select(Item)
            .where(*filters)
            .order_by(self._priority_sort(), Item.created_at.desc())
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
            .where(*filters)
            .order_by(self._priority_sort(), Item.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
