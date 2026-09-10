"""Pytest fixtures."""

from __future__ import annotations

import pytest
import pytest_asyncio

from taskbuddy.db import Database, TaskRepository


@pytest_asyncio.fixture
async def db(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    database = Database(url)
    await database.create_schema()
    yield database
    await database.dispose()


@pytest_asyncio.fixture
async def repo(db):
    async with db.session() as session:
        yield TaskRepository(session)
