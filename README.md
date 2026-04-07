# Personal Changelog

Track what you did day-to-day. Generate summaries for reflection, performance reviews, and career opportunities — powered by Claude.

## What it does

- Log entries from the CLI or API
- Tag and search entries
- Generate AI summaries across any date range in three modes:
  - **reflection** — narrative themes and patterns over the period
  - **perf_review** — impact-focused bullets for self-reviews and promos
  - **opportunities** — surfaces undersold strengths and framing gaps

## Stack

Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy (async), Alembic, Typer, Anthropic SDK

## Project structure

```
app/
  config.py               # Settings loaded from .env
  database.py             # Async SQLAlchemy engine and session factory
  models.py               # Entry and Summary ORM models
  schemas.py              # Pydantic request/response schemas
  exceptions.py           # Domain exceptions
  prompts.py              # LLM prompt templates for all three summary types
  main.py                 # FastAPI app with routers mounted
  cli.py                  # Typer CLI (add, today, list, search, edit, delete)
  api/
    deps.py               # FastAPI session dependency
    routes/
      entries.py          # /entries routes
      summaries.py        # /summaries routes
  services/
    entry_service.py      # Entry CRUD and search
    summary_service.py    # Summary generation and retrieval
    llm_client.py         # Anthropic API wrapper
alembic/
  env.py                  # Async Alembic migration runner
  versions/
    0001_initial.py       # Initial schema migration
tests/
  conftest.py             # In-memory SQLite fixtures and HTTP test client
  test_entry_service.py   # Unit tests for EntryService
  test_summary_service.py # Unit tests for SummaryService (LLM mocked)
  test_api_entries.py     # API tests for /entries routes
  test_api_summaries.py   # API tests for /summaries routes
```

## Setup

```bash
cp .env.example .env
# fill in DATABASE_URL and ANTHROPIC_API_KEY

pip install -e ".[dev]"
alembic upgrade head
```

## Running

```bash
# API
uvicorn app.main:app --reload

# CLI
changelog --help
changelog add "shipped the auth refactor" -t backend -t security
changelog today
changelog list --tag backend
changelog search "auth"
changelog edit <id> --content "updated content"
changelog delete <id>
```

## Tests

```bash
pytest
```

83 tests, no database or API key required.

## Not yet built

- CLI `summarize` command
- Auth / multi-user
