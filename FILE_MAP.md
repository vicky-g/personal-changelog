# File Map

## Config & Infrastructure

| File | Purpose |
|------|---------|
| `app/config.py` | Loads `DATABASE_URL` and `ANTHROPIC_API_KEY` from `.env` |
| `app/database.py` | Async SQLAlchemy engine, session factory, commit/rollback context manager |
| `app/main.py` | FastAPI app with entries, tags, and summary routers mounted |
| `alembic.ini` | Alembic configuration |
| `alembic/env.py` | Async migration runner that reads `DATABASE_URL` from settings |
| `alembic/versions/0001_initial.py` | Creates `entries`, `summaries`, enum types, and indexes |
| `alembic/versions/0002_add_entry_type.py` | Adds `entry_type` string column to `entries` |
| `pyproject.toml` | Project dependencies, build config, and pytest settings |
| `.env.example` | Template for required environment variables |

## Docker

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the app image; installs deps as a cached layer |
| `entrypoint.sh` | Runs migrations then starts uvicorn inside the container |
| `docker-compose.yml` | Defines `db` (PostgreSQL) and `app` services; wires them together |
| `.dockerignore` | Excludes `.env`, cache, and compiled files from the image |
| `scripts/start.sh` | Starts all services |
| `scripts/stop.sh` | Stops all services via `docker compose down` |

## Domain

| File | Purpose |
|------|---------|
| `app/models.py` | `Entry` (`entry_type` is a plain `String` column: `glow` \| `grow`), `Summary` ORM models; `is_editable` is a computed `@property` |
| `app/schemas.py` | Pydantic schemas for request validation and API response serialization; `EntryCreate.entry_type` validated as `Literal["glow", "grow"]` |
| `app/exceptions.py` | `AppError` base class with `http_status`; `EntryNotFound`, `EntryNotEditable`, `SummaryNotFound`, `NoEntriesFound` |
| `app/prompts.py` | System/user prompt pairs for `reflection`, `perf_review`, and `opportunities` |

## Services

| File | Purpose |
|------|---------|
| `app/services/entry_service.py` | Entry CRUD, multi-tag filtering, full-text search, and tag listing — all filterable by `entry_type` |
| `app/services/summary_service.py` | Fetches glows and grows for a date range, calls the LLM, saves and returns the result |
| `app/services/anthropic_llm_client.py` | Thin wrapper over the Anthropic Messages API |

## API

| File | Purpose |
|------|---------|
| `app/api/deps.py` | FastAPI `get_session` dependency |
| `app/api/routes/entries.py` | `GET/POST /entries`, `GET/PATCH/DELETE /entries/{id}`, `GET /entries/search`; `entry_type` required on POST, optional filter on GET |
| `app/api/routes/tags.py` | `GET /tags` — paginated list of unique tags with optional `entry_type` filter |
| `app/api/routes/summaries.py` | `POST /summaries/generate`, `GET /summaries`, `GET /summaries/{id}` |

## CLI

| File | Purpose |
|------|---------|
| `app/cli.py` | Typer commands: `add`, `today`, `yesterday`, `list`, `search`, `edit`, `delete`, `tags`; all support `--type glow\|grow` filter |

## Dev

| File | Purpose |
|------|---------|
| `requests.http` | Sample API requests for VS Code REST Client and JetBrains |

## Tests

| File | Purpose |
|------|---------|
| `tests/conftest.py` | In-memory SQLite session fixture and `httpx` test client with dependency override |
| `tests/test_entry_service.py` | Unit tests for tag normalization, 24hr edit window, CRUD, and search |
| `tests/test_summary_service.py` | Prompt selection, date range filtering, persistence, and `MockLLMClient` |
| `tests/test_api_entries.py` | Full HTTP round-trip tests for all `/entries` routes |
| `tests/test_api_summaries.py` | Full HTTP round-trip tests for all `/summaries` routes |
