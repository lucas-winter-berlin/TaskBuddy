"""Engine- und Session-Verwaltung."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base


def _ensure_item_numbers(connection) -> None:
    """Ergaenzt sichtbare Task-Nummern auf bestehenden Datenbanken."""
    inspector = inspect(connection)
    if "items" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("items")}
    if "number" not in columns:
        connection.execute(text("ALTER TABLE items ADD COLUMN number INTEGER"))
    connection.execute(text("UPDATE items SET number = id WHERE number IS NULL"))
    connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_items_user_number_active "
            "ON items (user_id, number) WHERE deleted_at IS NULL"
        )
    )


class Database:
    """Haelt Engine und Session-Factory und legt bei Bedarf das Schema an."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        connect_args: dict[str, object] = {}
        if url.startswith("sqlite"):
            connect_args["timeout"] = 30
        self.engine: AsyncEngine = create_async_engine(
            url, echo=echo, pool_pre_ping=True, connect_args=connect_args
        )
        self.session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def create_schema(self) -> None:
        """Legt fehlende Tabellen an. Ersetzt fuer den MVP ein Migrationstool."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_ensure_item_numbers)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Session mit Commit bei Erfolg und Rollback bei Fehler."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        await self.engine.dispose()
