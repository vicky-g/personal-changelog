# Personal Changelog

A tool for tracking what you do day-to-day. Then, generates AI-powered summaries for reflection.

## What it does

**Log entries** — add dated notes about your work, tagged however you like. Each entry has a type:

- `glow` — something that went well
- `grow` — something that could have gone better

**Search and browse** — full-text search across content and tags, filter by date, tag, or entry type.

**Generate summaries** — pick a date range and a mode:

- `reflection` — narrative summary of themes, patterns, and focus areas over the period
- `perf_review` — rewrites your entries as impact-focused bullets for self-reviews and promotion docs
- `opportunities` — analyzes what you're doing vs. how you're framing it; surfaces undersold strengths, framing gaps, and signals about how your role is evolving

---

## Prerequisites

- Python 3.11+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — includes the Docker CLI and runs the PostgreSQL container

## Local setup

```bash
git clone <repo>
cd personal-changelog

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY
```

---

## Running the app

`scripts/start.sh` starts the database, runs migrations, and starts the server in one command:

```bash
./scripts/start.sh
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

To stop:

```bash
./scripts/stop.sh          # stop, keep data
# OR
docker compose down -v     # stop and wipe data
```

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

`--type` is required. Use `glow` for things that went well, `grow` for things that could have gone better.

```bash
changelog add "shipped the auth refactor" --type glow
changelog add "led Q1 planning session" --type glow -t planning -t leadership
changelog add "underestimated the migration scope" --type grow -t planning
changelog add "fixed the memory leak in the worker" --type glow -t backend --date 2025-03-10
```

### View today's or yesterday's entries

```bash
# All entries today
changelog today

# All entries yesterday
changelog yesterday

# Only glows or grows
changelog today --type glow
changelog yesterday --type grow
```

### List and filter

```bash
# All recent entries
changelog list

# Filter by type
changelog list --type glow
changelog list --type grow

# Filter by date
changelog list --date 2025-03-10

# Filter by one or more tags
changelog list --tag backend
changelog list --tag backend --tag security

# Combine filters
changelog list --type glow --tag backend
```

### Search

```bash
# Search across all entries
changelog search "auth"

# Search within a specific type
changelog search "planning" --type grow
```

### Browse tags

```bash
# All unique tags
changelog tags

# Tags for a specific type
changelog tags --type glow

# Paginate
changelog tags --limit 20 --offset 0
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

---

## API

Full interactive docs at `http://localhost:8000/docs`.

### Entries

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/entries` | Create an entry (`entry_type` required in body) |
| `GET` | `/entries` | List entries (filter by `entry_type`, `date`, `tag`) |
| `GET` | `/entries/search` | Full-text search (optional `entry_type` filter) |
| `GET` | `/entries/{id}` | Get a single entry |
| `PATCH` | `/entries/{id}` | Update content or tags (within 24 hours) |
| `DELETE` | `/entries/{id}` | Delete an entry |

### Tags

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tags` | List all unique tags with pagination (optional `entry_type` filter) |

### Summaries

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/summaries/generate` | Generate a summary over a date range |
| `GET` | `/summaries` | List summaries (filter by `period_type` or `summary_type`) |
| `GET` | `/summaries/{id}` | Get a single summary |
