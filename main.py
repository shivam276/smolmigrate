import os
import asyncpg
import importlib
import argparse
import asyncio
from typing import List

DSN = os.environ["DSN"] 

async def migrations_init():
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
    applied_migrations = await run_pg_query("SELECT filename FROM pg_migrations ORDER BY id")
    return [row['filename'] for row in applied_migrations]

async def add_migration(filename: str, sql: str):
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
    try:
        with open(f"pg_migrations/{filename}.py", "w+") as file:
            file.write(f"up_sql = \"\"\"{sql}\"\"\"")
        
        await run_pg_query(sql)
        await run_pg_query("INSERT INTO pg_migrations (filename) VALUES ($1)", filename)
        
        print(f"Migration {filename} applied successfully")
    except Exception as e:
        print(f"Could not apply migration {filename}: {e}")
        os.remove(f"pg_migrations/{filename}.py")

async def apply_pending_migrations():
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
    applied_migrations = await get_applied_migrations()
    all_migrations = sorted([f[:-3] for f in os.listdir("pg_migrations") if f.endswith(".py") and f != "__init__.py"])
    
    for migration_file in all_migrations:
        if migration_file not in applied_migrations:
            module_name = f"pg_migrations.{migration_file}"
            migration_module = importlib.import_module(module_name)
            
            print(f"Applying migration: {migration_file}")
            await add_migration(migration_file, migration_module.up_sql)

async def run_pg_query(query: str, *args):
    if not DSN:
        raise ValueError("POSTGRES_DSN environment variable is not set")
    async with asyncpg.create_pool(DSN) as pool:
        async with pool.acquire() as connection:
            if args:
                return await connection.fetch(query, *args)
            else:
                return await connection.fetch(query)

async def create_migration(name: str):
    if not os.path.exists("pg_migrations"):
        print("Run migrations init!")
    migrations = os.listdir("pg_migrations")
    migration_number = len([f for f in migrations if f.endswith(".py") and f != "__init__.py"]) + 1
    filename = f"{migration_number:03d}_{name}.py"
    
    print("Enter your SQL query (press Enter twice to finish):")
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        else:
            break
    sql_query = "\n".join(lines)
    
    with open(f"pg_migrations/{filename}", "w") as f:
        f.write(f'up_sql = """\n{sql_query}\n"""')
    print(f"Created new migration file: {filename}")

async def list_migrations():
    applied_migrations = await get_applied_migrations()
    if os.path.exists("pg_migrations"):
        all_migrations = sorted([f[:-3] for f in os.listdir("pg_migrations") if f.endswith(".py") and f != "__init__.py"])
    else:
        print("Run migrations init!")
        return
    
    print("Migrations:")
    for migration in all_migrations:
        status = "Applied" if migration in applied_migrations else "Pending"
        print(f"  {migration}: {status}")

async def main():
    parser = argparse.ArgumentParser(description="Simple SQL Migration Tool")
    parser.add_argument("command", choices=["init", "migrate", "create", "list"],
                        help="Command to execute")
    parser.add_argument("--name", help="Name for the new migration (used with 'create' command)")

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

if __name__ == "__main__":
    asyncio.run(main())