# SMOLMIGRATE 

A lightweight(fits under 160 LOC) Python-based SQL migration tool for managing PostgreSQL database schema changes.

## Features

- Initialize migration setup
- Create new migrations
- Apply pending migrations
- List all migrations and their status
- Asynchronous execution using asyncio and asyncpg

## Requirements

- Python 3.7+
- asyncpg
- PostgreSQL database
- Docker (optional, for running PostgreSQL in a container)

## Setup

1. Install required packages:
   ```
   pip install -r requirements.txt 
   ```

2. Set your PostgreSQL connection string as an environment variable:
   ```
   export SMOLMIGRATE_DSN="your_postgres_connection_string"
   ```

3. (Optional) Use Docker to run PostgreSQL:
   ```
   docker-compose up -d
   ```

## Usage

Run the tool using the following command:
```
python main.py <command> [options]
```


Available commands:

- `init`: Initialize the migration setup
- `create --name <migration_name>`: Create a new migration
- `migrate`: Apply pending migrations
- `list`: List all migrations and their status

## Examples

1. Initialize migrations:
   ```
   python main.py init
   ```

2. Create a new migration:
   ```
   python main.py create --name add_users_table
   ```

3. Apply pending migrations:
   ```
   python main.py migrate
   ```

4. List all migrations:
   ```
   python main.py list
   ```

## Project Structure

- `main.py`: Core functionality of the migration tool
- `docker-compose.yml`: Docker configuration for PostgreSQL (optional)
- `main_test.py`: Test file for the migration tool

## Testing

Run tests using pytest:
