"""
API tests for /entries routes.

Uses a real FastAPI app + httpx AsyncClient against an in-memory SQLite DB.
No service-layer mocking — these test the full request/response cycle.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entry


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_entry(client: AsyncClient, **kwargs) -> dict:
    payload = {"content": "default content", **kwargs}
    r = await client.post("/entries", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ── POST /entries ──────────────────────────────────────────────────────────────

async def test_create_entry_returns_201(client: AsyncClient):
    r = await client.post("/entries", json={"content": "shipped the feature"})
    assert r.status_code == 201


async def test_create_entry_response_shape(client: AsyncClient):
    r = await client.post("/entries", json={"content": "wrote tests", "tags": ["testing"]})
    body = r.json()
    assert body["content"] == "wrote tests"
    assert body["tags"] == ["testing"]
    assert body["is_editable"] is True
    assert "id" in body
    assert "created_at" in body


async def test_create_entry_normalizes_tags(client: AsyncClient):
    r = await client.post("/entries", json={"content": "x", "tags": ["Python", "  BACKEND  "]})
    assert r.json()["tags"] == ["python", "backend"]


async def test_create_entry_explicit_date(client: AsyncClient):
    r = await client.post("/entries", json={"content": "backfill", "date": "2025-01-15"})
    assert r.json()["date"] == "2025-01-15"


async def test_create_entry_empty_content_returns_422(client: AsyncClient):
    r = await client.post("/entries", json={"content": ""})
    assert r.status_code == 422


async def test_create_entry_missing_content_returns_422(client: AsyncClient):
    r = await client.post("/entries", json={})
    assert r.status_code == 422


# ── GET /entries ───────────────────────────────────────────────────────────────

async def test_list_entries_empty(client: AsyncClient):
    r = await client.get("/entries")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_entries_returns_all(client: AsyncClient):
    await _create_entry(client, content="one")
    await _create_entry(client, content="two")
    r = await client.get("/entries")
    assert len(r.json()) == 2


async def test_list_entries_filter_by_date(client: AsyncClient):
    await _create_entry(client, content="target", date="2025-03-10")
    await _create_entry(client, content="other", date="2025-03-11")
    r = await client.get("/entries", params={"date": "2025-03-10"})
    body = r.json()
    assert len(body) == 1
    assert body[0]["content"] == "target"


async def test_list_entries_filter_by_tag(client: AsyncClient):
    await _create_entry(client, content="tagged", tags=["python"])
    await _create_entry(client, content="untagged")
    r = await client.get("/entries", params={"tag": "python"})
    body = r.json()
    assert len(body) == 1
    assert body[0]["content"] == "tagged"


async def test_list_entries_filter_by_multiple_tags(client: AsyncClient):
    await _create_entry(client, content="both", tags=["python", "backend"])
    await _create_entry(client, content="one only", tags=["python"])
    await _create_entry(client, content="neither")
    r = await client.get("/entries", params=[("tag", "python"), ("tag", "backend")])
    body = r.json()
    assert len(body) == 1
    assert body[0]["content"] == "both"


async def test_list_entries_limit(client: AsyncClient):
    for i in range(5):
        await _create_entry(client, content=f"entry {i}")
    r = await client.get("/entries", params={"limit": 3})
    assert len(r.json()) == 3


async def test_list_entries_offset(client: AsyncClient):
    for i in range(4):
        await _create_entry(client, content=f"entry {i}", date=f"2025-0{i+1}-01")
    r = await client.get("/entries", params={"limit": 2, "offset": 2})
    assert len(r.json()) == 2


# ── GET /entries/search ────────────────────────────────────────────────────────

async def test_search_matches_content(client: AsyncClient):
    await _create_entry(client, content="deployed the auth service")
    await _create_entry(client, content="reviewed pull requests")
    r = await client.get("/entries/search", params={"q": "auth"})
    body = r.json()
    assert len(body) == 1
    assert "auth" in body[0]["content"]


async def test_search_matches_tags(client: AsyncClient):
    await _create_entry(client, content="infra work", tags=["infrastructure"])
    await _create_entry(client, content="other work", tags=["frontend"])
    r = await client.get("/entries/search", params={"q": "infrastructure"})
    assert len(r.json()) == 1


async def test_search_case_insensitive(client: AsyncClient):
    await _create_entry(client, content="Refactored the Database")
    r = await client.get("/entries/search", params={"q": "database"})
    assert len(r.json()) == 1


async def test_search_no_results(client: AsyncClient):
    await _create_entry(client, content="something else")
    r = await client.get("/entries/search", params={"q": "xyzzy"})
    assert r.json() == []


async def test_search_missing_query_returns_422(client: AsyncClient):
    r = await client.get("/entries/search")
    assert r.status_code == 422


# ── GET /entries/{id} ─────────────────────────────────────────────────────────

async def test_get_entry_by_id(client: AsyncClient):
    created = await _create_entry(client, content="findable")
    r = await client.get(f"/entries/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_entry_not_found(client: AsyncClient):
    r = await client.get(f"/entries/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_get_entry_invalid_uuid_returns_422(client: AsyncClient):
    r = await client.get("/entries/not-a-uuid")
    assert r.status_code == 422


# ── PATCH /entries/{id} ───────────────────────────────────────────────────────

async def test_update_entry_content(client: AsyncClient):
    created = await _create_entry(client, content="original")
    r = await client.patch(f"/entries/{created['id']}", json={"content": "revised"})
    assert r.status_code == 200
    assert r.json()["content"] == "revised"


async def test_update_entry_tags(client: AsyncClient):
    created = await _create_entry(client, content="work", tags=["old"])
    r = await client.patch(f"/entries/{created['id']}", json={"tags": ["NEW", "tags"]})
    assert r.status_code == 200
    assert r.json()["tags"] == ["new", "tags"]


async def test_update_entry_not_found(client: AsyncClient):
    r = await client.patch(f"/entries/{uuid.uuid4()}", json={"content": "x"})
    assert r.status_code == 404


async def test_update_locked_entry_returns_403(
    client: AsyncClient, session: AsyncSession
):
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    entry = Entry(
        content="old entry",
        date=date(2025, 1, 1),
        tags=[],
        created_at=old_time,
        updated_at=old_time,
    )
    session.add(entry)
    await session.flush()

    r = await client.patch(f"/entries/{entry.id}", json={"content": "too late"})
    assert r.status_code == 403


# ── DELETE /entries/{id} ──────────────────────────────────────────────────────

async def test_delete_entry_returns_204(client: AsyncClient):
    created = await _create_entry(client, content="delete me")
    r = await client.delete(f"/entries/{created['id']}")
    assert r.status_code == 204


async def test_delete_entry_is_gone(client: AsyncClient):
    created = await _create_entry(client, content="delete me")
    await client.delete(f"/entries/{created['id']}")
    r = await client.get(f"/entries/{created['id']}")
    assert r.status_code == 404


async def test_delete_entry_not_found(client: AsyncClient):
    r = await client.delete(f"/entries/{uuid.uuid4()}")
    assert r.status_code == 404
