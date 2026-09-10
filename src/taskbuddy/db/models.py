"""SQLAlchemy-Modelle. Laufen unveraendert auf SQLite und PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# BIGSERIAL/BIGINT gibt es in SQLite nicht als Autoincrement-PK, daher Variante.
PKType = BigInteger().with_variant(Integer(), "sqlite")


def utcnow() -> datetime:
    """Zeitzonen-bewusstes Jetzt in UTC."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """SQLite liefert naive Datetimes zurueck; die gelten hier als UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).isoformat()


class Base(DeclarativeBase):
    pass


class Project(Base):
    """Privat, Arbeit oder ein selbst angelegtes Projekt."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="custom")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_projects_user_key"),
        Index("ix_projects_user_active", "user_id", "deleted_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "kind": self.kind,
            "created_at": _iso(self.created_at),
        }


class Item(Base):
    """Aufgabe oder Notiz in einem Projekt."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(
        PKType, ForeignKey("projects.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # task | note
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    # Nur Tasks: A|B|C|D. Notizen: null.
    priority: Mapped[str | None] = mapped_column(String(1))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_items_user_type_active", "user_id", "type", "deleted_at"),
        Index("ix_items_user_project_active", "user_id", "project_id", "deleted_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "priority": self.priority,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
