# SMOLMIGRATE 

A lightweight (under 160 LOC) Python-based SQL migration tool for managing PostgreSQL database schema changes.

## Features

- Initialize migration setup
- Create new migrations with up/down SQL
- Apply pending migrations
- Rollback migrations (last, specific, or all)
- List all migrations and their status
- Asynchronous execution using asyncio and asyncpg

## Requirements

- Python 3.7+
- asyncpg
- PostgreSQL database
- Docker (optional, for running PostgreSQL in a container)

## Setup

1. Install required packages:
   ```bash
   pip install -r requirements.txt 
   ```

2. Set your PostgreSQL connection string as an environment variable:
   ```bash
   export SMOLMIGRATE_DSN="postgresql://user:password@localhost:5432/dbname"
   ```

3. (Optional) Use Docker to run PostgreSQL:
   ```bash
   docker-compose up -d
   ```

## Usage

```bash
python main.py <command> [options]
```

### Available Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize migration setup |
| `create --name <name>` | Create a new migration |
| `migrate` | Apply pending migrations |
| `list` | List all migrations with status |
| `rollback` | Rollback last applied migration |
| `rollback --all` | Rollback all migrations |
| `rollback --migration <name>` | Rollback specific migration |

## Examples

### 1. Initialize migrations
```bash
python main.py init
```

### 2. Create a new migration
```bash
python main.py create --name add_users_table
# Enter UP SQL: CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT);
# Enter DOWN SQL: DROP TABLE users;
```

### 3. Apply pending migrations
```bash
python main.py migrate
```

### 4. List all migrations
```bash
python main.py list
# Output:
# Migrations:
#   [Applied] 001_initial
#   [Pending] 002_add_users_table
```

### 5. Rollback last migration
```bash
python main.py rollback
```

### 6. Rollback all migrations
```bash
python main.py rollback --all
```

### 7. Rollback specific migration
```bash
python main.py rollback --migration 002_add_users_table
```

## Migration File Format

Each migration file contains both `up_sql` and `down_sql`:

```python
up_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

down_sql = """
DROP TABLE users;
"""
```

## Project Structure

```
smolmigrate/
├── main.py              # Core migration tool
├── main_test.py         # Test suite
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker config for PostgreSQL
├── README.md            # This file
└── pg_migrations/       # Migration files (created on init)
    ├── 001_initial.py
    └── 002_add_users.py
```

## Testing

Run tests using pytest:
```bash
pytest main_test.py -v
```

## License

MIT
