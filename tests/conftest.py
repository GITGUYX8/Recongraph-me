import os
import tempfile

# Give tests an isolated SQLite database so they do not touch the local
# development database. Set before importing the app.
_tmpdir = tempfile.mkdtemp(prefix="recongraph-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmpdir}/test.db"
os.environ["RECONGRAPH_UPLOAD_DIR"] = f"{_tmpdir}/uploads"


import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    import asyncio

    import app.database as database
    import app.models as models

    async def _setup():
        async with database.engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.run(_setup())
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """Reset all tables before each test for full isolation."""
    import asyncio

    import sqlalchemy as sa

    import app.database as database
    import app.models as models

    async def _clean():
        async with database.engine.begin() as conn:
            for table in reversed(models.Base.metadata.sorted_tables):
                await conn.execute(sa.text(f"DELETE FROM {table.name}"))

    asyncio.run(_clean())
    yield