import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Set env var before importing main
os.environ["SMOLMIGRATE_DSN"] = "postgresql://test:test@localhost:5432/test"

from main import (
    migrations_init,
    add_migration,
    apply_pending_migrations,
    create_migration,
    list_migrations,
    check_pg_migrations_exists,
    get_applied_migrations,
    run_pg_query
)


@pytest.fixture(autouse=True)
def mock_db():
    """Mock all database operations"""
    with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = [{"exists": True}, {"filename": "001_initial.py"}]
        yield mock_query


@pytest.fixture
def clean_migration_dir(tmp_path):
    """Create a temporary migration directory"""
    migration_dir = tmp_path / "pg_migrations"
    migration_dir.mkdir()
    return tmp_path


class TestMigrationsInit:
    @pytest.mark.asyncio
    async def test_init_creates_directory(self, tmp_path, mock_db):
        """Test that init creates pg_migrations directory"""
        os.chdir(tmp_path)
        
        with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []
            await migrations_init()
        
        assert os.path.exists("pg_migrations")

    @pytest.mark.asyncio
    async def test_init_already_exists(self, tmp_path, mock_db, capsys):
        """Test that init handles existing directory"""
        os.chdir(tmp_path)
        os.makedirs("pg_migrations")
        
        await migrations_init()
        
        captured = capsys.readouterr()
        assert "already been initialized" in captured.out


class TestAddMigration:
    @pytest.mark.asyncio
    async def test_add_migration_creates_file(self, tmp_path, mock_db):
        """Test that add_migration creates migration file"""
        os.chdir(tmp_path)
        os.makedirs("pg_migrations")
        
        with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []
            await add_migration("test_migration", "SELECT 1;")
        
        assert os.path.exists("pg_migrations/test_migration.py")

    @pytest.mark.asyncio
    async def test_add_migration_without_init(self, tmp_path, capsys):
        """Test that add_migration fails without init"""
        os.chdir(tmp_path)
        
        await add_migration("test", "SELECT 1;")
        
        captured = capsys.readouterr()
        assert "Run migrations init" in captured.out


class TestCheckMigrationsExists:
    @pytest.mark.asyncio
    async def test_check_returns_true(self, mock_db):
        """Test that check_pg_migrations_exists returns True when table exists"""
        with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"exists": True}]
            result = await check_pg_migrations_exists()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_returns_false_on_error(self):
        """Test that check_pg_migrations_exists returns False on error"""
        with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = Exception("Connection failed")
            result = await check_pg_migrations_exists()
            assert result is False


class TestGetAppliedMigrations:
    @pytest.mark.asyncio
    async def test_gets_applied_migrations(self):
        """Test retrieving applied migrations"""
        with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [
                {"filename": "001_initial.py"},
                {"filename": "002_add_users.py"}
            ]
            result = await get_applied_migrations()
            assert result == ["001_initial.py", "002_add_users.py"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self):
        """Test returns empty list when no migrations applied"""
        with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []
            result = await get_applied_migrations()
            assert result == []


class TestListMigrations:
    @pytest.mark.asyncio
    async def test_list_shows_pending_and_applied(self, tmp_path, capsys):
        """Test list command shows correct status"""
        os.chdir(tmp_path)
        os.makedirs("pg_migrations")
        
        # Create some migration files
        with open("pg_migrations/001_initial.py", "w") as f:
            f.write('up_sql = """SELECT 1;"""')
        with open("pg_migrations/002_add_users.py", "w") as f:
            f.write('up_sql = """SELECT 2;"""')
        
        with patch("main.run_pg_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"filename": "001_initial.py"}]
            await list_migrations()
        
        captured = capsys.readouterr()
        assert "001_initial" in captured.out
        assert "002_add_users" in captured.out


class TestCreateMigration:
    @pytest.mark.asyncio
    async def test_create_migration_file(self, tmp_path):
        """Test creating a new migration file"""
        os.chdir(tmp_path)
        os.makedirs("pg_migrations")
        
        # Mock user input
        with patch("builtins.input", side_effect=["SELECT 1;", ""]):
            with patch("main.pg_metadata_init", new_callable=AsyncMock):
                await create_migration("test_migration")
        
        files = os.listdir("pg_migrations")
        assert any("test_migration" in f for f in files)


class TestRunPgQuery:
    @pytest.mark.asyncio
    async def test_query_without_args(self):
        """Test running a query without arguments"""
        with patch("asyncpg.create_pool") as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = [{"id": 1}]
            
            mock_pool_cm = AsyncMock()
            mock_pool_cm.__aenter__.return_value.acquire = MagicMock(
                return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_conn))
            )
            mock_pool.return_value = mock_pool_cm
            
            result = await run_pg_query("SELECT 1")
            assert result == [{"id": 1}]


# Cleanup after tests
@pytest.fixture(autouse=True)
def cleanup(tmp_path):
    """Clean up any created directories"""
    yield
    if os.path.exists("pg_migrations"):
        import shutil
        shutil.rmtree("pg_migrations", ignore_errors=True)
