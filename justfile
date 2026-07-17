set shell := ["powershell", "-Command"]

# Start the development server on port 8000 (aligned with Vite proxy target)
dev:
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Start the background worker for document ingestion tasks
worker:
    uv run arq worker.main.WorkerSettings

# Spawn a new shell with the virtual environment activated : just venv
venv:
    powershell -NoExit -ExecutionPolicy Bypass -File .venv\Scripts\Activate.ps1

# Auto-generate a new database migration
# Usage: just migration "added users table"
migration msg="auto":
    uv run alembic revision --autogenerate -m "{{msg}}"

# Run all pending migrations : just migrate
migrate:
    uv run alembic upgrade head

# Run seeders : just seed
seed:
    uv run python scripts/seed_db.py

# Format code using ruff : just format
format:
    uv run ruff check . --fix
    uv run ruff format .

# Run sonarqube analysis (reads config from sonar-project.properties)
sonar:
    uv run pysonar

# Check code without modifying (useful for CI)
lint:
    uv run ruff check .
    uv run ruff format --check .

# Start the infrastructure containers (Postgres, Qdrant, Redis, Adminer) : just docker-up
docker-up:
    docker-compose up -d

# Stop the infrastructure containers : just docker-down
docker-down:
    docker-compose down

# View logs for the infrastructure containers : just docker-logs
docker-logs:
    docker-compose logs -f

# View status of the infrastructure containers : just docker-ps
docker-ps:
    docker-compose ps
