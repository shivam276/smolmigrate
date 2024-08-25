import os
import pytest
os.environ["POSTGRES_DSN"] = "DSN"
from main import migrations_init, add_migrations
@pytest.mark.asyncio(loop_scope="module")
async def test_init():
    await migrations_init()
    directories = os.listdir()
    assert "pg_migrations" in directories
    files_in_directory = os.listdir("./pg_migrations")
    assert "migrations_completed.py" in files_in_directory

@pytest.mark.asyncio(loop_scope="module")
async def test_run_migration():
    length_before_migration = len(os.listdir("pg_migrations"))
    await add_migrations("SQL")
    length_after_migration = len(os.listdir("pg_migrations"))
    assert length_after_migration == length_before_migration + 1
    