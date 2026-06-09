"""
Unit tests for EntryService.

Covers:
- 24-hour edit window enforcement
- Tag normalization (lowercase, strip whitespace, deduplicate empties)
- Basic CRUD operations
- Search
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entry
from app.exceptions import EntryNotEditable, EntryNotFound
from app.schemas import EntryCreate, EntryUpdate
from app.services.entry_service import EntryService


# ── Helpers ────────────────────────────────────────────────────────────────────

def _entry(session: AsyncSession, **kwargs) -> Entry:
    """Build and add an Entry directly, bypassing the service, for fixture setup."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        entry_type="glow",
        content="default content",
        date=date.today(),
        tags=[],
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    entry = Entry(**defaults)
    session.add(entry)
    return entry


# ── Tag normalization ──────────────────────────────────────────────────────────

async def test_tags_lowercased_on_create(session: AsyncSession):
    service = EntryService(session)
    data = EntryCreate(entry_type="glow",content="Did the thing", tags=["PYTHON", "FastAPI", "Dev-Ops"])
    entry = await service.create(data)
    assert entry.tags == ["python", "fastapi", "dev-ops"]


async def test_tags_whitespace_stripped_on_create(session: AsyncSession):
    service = EntryService(session)
    data = EntryCreate(entry_type="glow",content="Shipped it", tags=["  frontend  ", " CSS"])
    entry = await service.create(data)
    assert entry.tags == ["frontend", "css"]


async def test_empty_tags_filtered_on_create(session: AsyncSession):
    service = EntryService(session)
    data = EntryCreate(entry_type="glow",content="Work work", tags=["valid", "  ", ""])
    entry = await service.create(data)
    assert entry.tags == ["valid"]


async def test_tags_lowercased_on_update(session: AsyncSession):
    service = EntryService(session)
    entry = await service.create(EntryCreate(entry_type="glow",content="initial", tags=["python"]))
    updated = await service.update(entry.id, EntryUpdate(tags=["PYTHON", "Go"]))
    assert updated.tags == ["python", "go"]


async def test_empty_tags_list_on_create(session: AsyncSession):
    service = EntryService(session)
    entry = await service.create(EntryCreate(entry_type="glow",content="No tags here"))
    assert entry.tags == []


# ── 24-hour edit window ────────────────────────────────────────────────────────

async def test_entry_is_editable_within_24hrs(session: AsyncSession):
    service = EntryService(session)
    entry = await service.create(EntryCreate(entry_type="glow",content="fresh entry"))
    assert entry.is_editable is True


async def test_entry_is_not_editable_after_24hrs(session: AsyncSession):
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    entry = _entry(session, content="old entry", created_at=old_time, updated_at=old_time)
    await session.flush()
    assert entry.is_editable is False


async def test_update_raises_when_entry_locked(session: AsyncSession):
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    entry = _entry(session, content="stale entry", created_at=old_time, updated_at=old_time)
    await session.flush()

    service = EntryService(session)
    with pytest.raises(EntryNotEditable):
        await service.update(entry.id, EntryUpdate(content="too late"))


async def test_update_succeeds_within_24hrs(session: AsyncSession):
    service = EntryService(session)
    entry = await service.create(EntryCreate(entry_type="glow",content="original"))
    updated = await service.update(entry.id, EntryUpdate(content="revised"))
    assert updated.content == "revised"


async def test_entry_exactly_at_24hr_boundary_is_not_editable(session: AsyncSession):
    # Created exactly 24 hours ago (+ 1 second) should be locked
    old_time = datetime.now(timezone.utc) - timedelta(hours=24, seconds=1)
    entry = _entry(session, content="boundary entry", created_at=old_time, updated_at=old_time)
    await session.flush()
    assert entry.is_editable is False


async def test_entry_just_under_24hr_boundary_is_editable(session: AsyncSession):
    recent_time = datetime.now(timezone.utc) - timedelta(hours=23, minutes=59)
    entry = _entry(session, content="almost locked", created_at=recent_time, updated_at=recent_time)
    await session.flush()
    assert entry.is_editable is True


# ── CRUD ───────────────────────────────────────────────────────────────────────

async def test_create_sets_date_to_today_by_default(session: AsyncSession):
    service = EntryService(session)
    entry = await service.create(EntryCreate(entry_type="glow",content="daily standup notes"))
    assert entry.date == date.today()


async def test_create_with_explicit_date(session: AsyncSession):
    service = EntryService(session)
    target = date(2025, 3, 15)
    entry = await service.create(EntryCreate(entry_type="glow",content="backfill", date=target))
    assert entry.date == target


async def test_get_returns_entry(session: AsyncSession):
    service = EntryService(session)
    created = await service.create(EntryCreate(entry_type="glow",content="findable"))
    fetched = await service.get(created.id)
    assert fetched.id == created.id
    assert fetched.content == "findable"


async def test_get_raises_for_unknown_id(session: AsyncSession):
    service = EntryService(session)
    with pytest.raises(EntryNotFound):
        await service.get(uuid.uuid4())


async def test_list_returns_all_entries(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="entry one"))
    await service.create(EntryCreate(entry_type="glow",content="entry two"))
    entries = await service.list_entries()
    assert len(entries) == 2


async def test_list_filters_by_date(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="today", date=date.today()))
    await service.create(EntryCreate(entry_type="glow",content="yesterday", date=date(2020, 1, 1)))
    entries = await service.list_entries(date=date.today())
    assert len(entries) == 1
    assert entries[0].content == "today"


async def test_list_filters_by_tag(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="tagged", tags=["python"]))
    await service.create(EntryCreate(entry_type="glow",content="untagged"))
    entries = await service.list_entries(tags=["python"])
    assert len(entries) == 1
    assert entries[0].content == "tagged"


async def test_list_filters_by_multiple_tags(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="both", tags=["python", "backend"]))
    await service.create(EntryCreate(entry_type="glow",content="one tag", tags=["python"]))
    await service.create(EntryCreate(entry_type="glow",content="neither"))
    entries = await service.list_entries(tags=["python", "backend"])
    assert len(entries) == 1
    assert entries[0].content == "both"


async def test_delete_removes_entry(session: AsyncSession):
    service = EntryService(session)
    entry = await service.create(EntryCreate(entry_type="glow",content="delete me"))
    await service.delete(entry.id)
    with pytest.raises(EntryNotFound):
        await service.get(entry.id)


async def test_delete_raises_for_unknown_id(session: AsyncSession):
    service = EntryService(session)
    with pytest.raises(EntryNotFound):
        await service.delete(uuid.uuid4())


# ── Search ─────────────────────────────────────────────────────────────────────

async def test_search_matches_content(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="deployed the authentication service"))
    await service.create(EntryCreate(entry_type="glow",content="reviewed pull requests"))
    results = await service.search("authentication")
    assert len(results) == 1
    assert "authentication" in results[0].content


async def test_search_is_case_insensitive(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="Refactored the Database layer"))
    results = await service.search("database")
    assert len(results) == 1


async def test_search_matches_tags(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="some work", tags=["infrastructure"]))
    await service.create(EntryCreate(entry_type="glow",content="other work", tags=["frontend"]))
    results = await service.search("infrastructure")
    assert len(results) == 1
    assert results[0].tags == ["infrastructure"]


async def test_search_empty_query_returns_empty(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="some content"))
    results = await service.search("")
    assert results == []


async def test_search_no_matches_returns_empty(session: AsyncSession):
    service = EntryService(session)
    await service.create(EntryCreate(entry_type="glow",content="completely unrelated"))
    results = await service.search("xyzzy_not_found")
    assert results == []
