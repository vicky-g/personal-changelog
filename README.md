# Personal Changelog

A tool for tracking what you do day-to-day and turning it into something useful. Log entries from the CLI or API, then generate AI-powered summaries for reflection, performance reviews, or career development.

## What it does

**Log entries** — add dated notes about your work, tagged however you like.

**Search and browse** — full-text search across content and tags, filter by date or tag.

**Generate summaries** — pick a date range and a mode:

- `reflection` — narrative summary of themes, patterns, and focus areas over the period
- `perf_review` — rewrites your entries as impact-focused bullets for self-reviews and promotion docs
- `opportunities` — analyzes what you're doing vs. how you're framing it; surfaces undersold strengths, framing gaps, and signals about how your role is evolving

---

## Local setup

**Requirements:** Python 3.11+, PostgreSQL

```bash
git clone <repo>
cd personal-changelog

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and set:
#   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/personal_changelog
#   ANTHROPIC_API_KEY=sk-ant-...

# Run migrations
alembic upgrade head
```

---

## Running the API

```bash
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

---

## Running tests

No database or API key required — tests use an in-memory SQLite database and mock the LLM.

```bash
pytest
```

---

## CLI

```bash
changelog --help
```

### Add an entry

```bash
changelog add "shipped the auth refactor"
changelog add "led Q1 planning session" -t planning -t leadership
changelog add "fixed the memory leak in the worker" -t backend --date 2025-03-10
```

### View today's entries

```bash
changelog today
```

### List and filter

```bash
# All recent entries
changelog list

# Filter by date
changelog list --date 2025-03-10

# Filter by one or more tags
changelog list --tag backend
changelog list --tag backend --tag security
```

### Search

```bash
changelog search "auth"
changelog search "planning"
```

### Edit an entry

Entries are editable within 24 hours of creation.

```bash
changelog edit <id> --content "updated content"
changelog edit <id> --tag backend --tag infra
```

### Delete an entry

```bash
changelog delete <id>
changelog delete <id> --yes   # skip confirmation
```
