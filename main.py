import os
from typing import List, Optional
import asyncpg
import importlib
import argparse
import asyncio

DSN = os.environ.get("SMOLMIGRATE_DSN", "")


async def run_pg_query(query: str, *args):
    """Execute a PostgreSQL query and return results"""
    if not DSN:
        raise ValueError("SMOLMIGRATE_DSN environment variable is not set")
    async with asyncpg.create_pool(DSN) as pool:
        async with pool.acquire() as connection:
            if args:
                return await connection.fetch(query, *args)
            else:
                return await connection.fetch(query)


async def check_pg_migrations_exists() -> bool:
    """Check if pg_migrations table exists"""
    try:
        result = await run_pg_query("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'pg_migrations'
            )
        """)
        return result[0]['exists']
    except Exception as e:
        print(f"Error checking if pg_migrations table exists: {e}")
        return False


async def pg_metadata_init():
    """Initialize the pg_migrations table if it doesn't exist"""
    try:
        if not await check_pg_migrations_exists():
            await run_pg_query("""
                CREATE TABLE IF NOT EXISTS pg_migrations (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    except Exception as e:
        print(f"Failed to init pg_metadata: {e}")


async def migrations_init():
    """Initialize migration system - create directory and table"""
    directories = os.listdir()
    if "pg_migrations" not in directories:
        os.makedirs("pg_migrations")
        print("Created pg_migrations directory.")
        await run_pg_query("""
            CREATE TABLE IF NOT EXISTS pg_migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Initialized migrations table in the database.")
    else:
        print("A pg_migrations process has already been initialized")


async def get_applied_migrations() -> List[str]:
    """Get list of applied migration filenames"""
    applied_migrations = await run_pg_query("SELECT filename FROM pg_migrations ORDER BY id")
    return [row['filename'] for row in applied_migrations]


async def get_last_applied_migration() -> Optional[str]:
    """Get the most recently applied migration"""
    result = await run_pg_query("SELECT filename FROM pg_migrations ORDER BY id DESC LIMIT 1")
    if result:
        return result[0]['filename']
    return None


async def add_migration(filename: str, sql: str):
    """Apply a migration and record it"""
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
        return
    try:
        # Create migration file
        with open(f"pg_migrations/{filename}.py", "w+") as file:
            file.write(f'up_sql = """{sql}"""\n')
        
        # Execute migration
        await run_pg_query(sql)
        await run_pg_query("INSERT INTO pg_migrations (filename) VALUES ($1)", filename)
        
        print(f"Migration {filename} applied successfully")
    except Exception as e:
        print(f"Could not apply migration {filename}: {e}")
        if os.path.exists(f"pg_migrations/{filename}.py"):
            os.remove(f"pg_migrations/{filename}.py")


async def apply_pending_migrations():
    """Apply all pending migrations"""
    if not os.path.exists("pg_migrations"): 
        print("Run migrations init!")
        return
    await pg_metadata_init()
    
    applied_migrations = await get_applied_migrations()
    all_migrations = sorted([f[:-3] for f in os.listdir("pg_migrations") if f.endswith(".py") and f != "__init__.py"])
    
    for migration_file in all_migrations:
        if migration_file not in applied_migrations:
            module_name = f"pg_migrations.{migration_file}"
            migration_module = importlib.import_module(module_name)
            
            print(f"Applying migration: {migration_file}")
            await add_migration(migration_file, migration_module.up_sql)


async def rollback_migration(migration_name: Optional[str] = None):
    """Rollback a specific migration or the last applied one"""
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
        return
    
    await pg_metadata_init()
    
    if migration_name:
        target_migration = migration_name
    else:
        target_migration = await get_last_applied_migration()
        if not target_migration:
            print("No migrations to rollback")
            return
    
    # Check if migration was applied
    applied = await get_applied_migrations()
    if target_migration not in applied:
        print(f"Migration {target_migration} is not applied, cannot rollback")
        return
    
    # Load migration module and get down_sql
    module_name = f"pg_migrations.{target_migration}"
    try:
        migration_module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(f"Migration file not found: {target_migration}")
        return
    
    down_sql = getattr(migration_module, 'down_sql', None)
    if not down_sql:
        print(f"No down_sql found in {target_migration}, cannot rollback")
        print("Hint: Add down_sql to your migration file")
        return
    
    try:
        print(f"Rolling back migration: {target_migration}")
        await run_pg_query(down_sql)
        await run_pg_query("DELETE FROM pg_migrations WHERE filename = $1", target_migration)
        print(f"Migration {target_migration} rolled back successfully")
    except Exception as e:
        print(f"Error rolling back migration {target_migration}: {e}")


async def rollback_all():
    """Rollback all applied migrations in reverse order"""
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
        return
    
    await pg_metadata_init()
    
    applied = await get_applied_migrations()
    if not applied:
        print("No migrations to rollback")
        return
    
    # Rollback in reverse order
    for migration in reversed(applied):
        await rollback_migration(migration)
    
    print("All migrations rolled back")


async def create_migration(name: str):
    """Create a new migration file with up and down SQL"""
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
        return
    await pg_metadata_init()
    migrations = os.listdir("pg_migrations")
    migration_number = len([f for f in migrations if f.endswith(".py") and f != "__init__.py"]) + 1
    filename = f"{migration_number:03d}_{name}.py"
    
    print("Enter UP SQL query (press Enter twice to finish):")
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        else:
            break
    up_sql = "\n".join(lines)
    
    print("Enter DOWN SQL query (press Enter twice to finish):")
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        else:
            break
    down_sql = "\n".join(lines)
    
    with open(f"pg_migrations/{filename}", "w") as f:
        f.write(f'up_sql = """\n{up_sql}\n"""\n\n')
        f.write(f'down_sql = """\n{down_sql}\n"""\n')
    print(f"Created new migration file: {filename}")


async def list_migrations():
    """List all migrations with their status"""
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
        return
    await pg_metadata_init()
    
    all_migrations = sorted([f[:-3] for f in os.listdir("pg_migrations") if f.endswith(".py") and f != "__init__.py"])
    applied_migrations = await get_applied_migrations()
    
    print("Migrations:")
    for migration in all_migrations:
        status = "Applied" if migration in applied_migrations else "Pending"
        print(f"  [{status}] {migration}")


async def main():
    parser = argparse.ArgumentParser(description="Simple SQL Migration Tool")
    parser.add_argument("command", choices=["init", "migrate", "create", "list", "rollback"],
                        help="Command to execute")
    parser.add_argument("--name", help="Name for the new migration (used with 'create' command)")
    parser.add_argument("--all", action="store_true", help="Rollback all migrations (used with 'rollback')")
    parser.add_argument("--migration", help="Specific migration to rollback (used with 'rollback')")

    args = parser.parse_args()

    if args.command == "init":
        await migrations_init()
    elif args.command == "migrate":
        await apply_pending_migrations()
    elif args.command == "create":
        if not args.name:
            print("Error: --name is required for the 'create' command")
            return
        await create_migration(args.name)
    elif args.command == "list":
        await list_migrations()
    elif args.command == "rollback":
        if args.all:
            await rollback_all()
        else:
            await rollback_migration(args.migration)


if __name__ == "__main__":
    asyncio.run(main())
