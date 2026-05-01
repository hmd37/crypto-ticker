import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from database import Base


@pytest.fixture
async def session():
    engine = create_async_engine("postgresql+asyncpg://ahmad:12345@localhost/test_db")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as s:
        yield s
        await s.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
