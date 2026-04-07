"""
API tests for /summaries routes.

LLMClient is patched at the class level in summary_service so no real API
calls are made. Entry data is seeded via the /entries API.
"""

import uuid
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────────

@contextmanager
def _mock_llm(response_text: str):
    """Patch LLMClient.complete for the duration of a with-block."""
    with patch("app.services.summary_service.LLMClient") as MockCls:
        MockCls.return_value.complete.return_value = response_text
        yield MockCls


async def _seed_entry(client: AsyncClient, content: str, date: str) -> dict:
    r = await client.post("/entries", json={"content": content, "date": date})
    assert r.status_code == 201
    return r.json()


WEEKLY_PAYLOAD = {
    "period_type": "weekly",
    "start_date": "2025-03-10",
    "end_date": "2025-03-16",
    "summary_type": "reflection",
}


# ── POST /summaries/generate ──────────────────────────────────────────────────

async def test_generate_returns_201(client: AsyncClient):
    await _seed_entry(client, "shipped feature", "2025-03-12")

    with _mock_llm("Great week."):
        r = await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)

    assert r.status_code == 201


async def test_generate_response_shape(client: AsyncClient):
    await _seed_entry(client, "led design review", "2025-03-11")

    with _mock_llm("You led things."):
        r = await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)

    body = r.json()
    assert body["generated_text"] == "You led things."
    assert body["period_type"] == "weekly"
    assert body["summary_type"] == "reflection"
    assert body["start_date"] == "2025-03-10"
    assert body["end_date"] == "2025-03-16"
    assert "id" in body
    assert "created_at" in body


async def test_generate_perf_review_type(client: AsyncClient):
    await _seed_entry(client, "reduced latency by 40%", "2025-03-13")

    payload = {**WEEKLY_PAYLOAD, "summary_type": "perf_review"}
    with _mock_llm("- Reduced latency by 40%"):
        r = await client.post("/summaries/generate", json=payload)

    assert r.status_code == 201
    assert r.json()["summary_type"] == "perf_review"


async def test_generate_opportunities_type(client: AsyncClient):
    await _seed_entry(client, "mentored two engineers", "2025-03-14")

    payload = {**WEEKLY_PAYLOAD, "summary_type": "opportunities"}
    with _mock_llm("You're underselling your leadership."):
        r = await client.post("/summaries/generate", json=payload)

    assert r.status_code == 201
    assert r.json()["summary_type"] == "opportunities"


async def test_generate_no_entries_returns_422(client: AsyncClient):
    with _mock_llm(""):
        r = await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)

    assert r.status_code == 422
    assert "No entries found" in r.json()["detail"]


async def test_generate_entries_outside_range_returns_422(client: AsyncClient):
    await _seed_entry(client, "out of range entry", "2025-01-01")

    with _mock_llm(""):
        r = await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)

    assert r.status_code == 422


async def test_generate_invalid_period_type_returns_422(client: AsyncClient):
    payload = {**WEEKLY_PAYLOAD, "period_type": "daily"}
    r = await client.post("/summaries/generate", json=payload)
    assert r.status_code == 422


async def test_generate_invalid_summary_type_returns_422(client: AsyncClient):
    payload = {**WEEKLY_PAYLOAD, "summary_type": "vibes"}
    r = await client.post("/summaries/generate", json=payload)
    assert r.status_code == 422


async def test_generate_bullets_extracted_and_saved(client: AsyncClient):
    await _seed_entry(client, "drove alignment", "2025-03-12")
    generated = "- Drove alignment across four teams\n- Cut deploy time by 30%"

    with _mock_llm(generated):
        r = await client.post(
            "/summaries/generate", json={**WEEKLY_PAYLOAD, "summary_type": "perf_review"}
        )

    body = r.json()
    assert body["raw_bullets"] == [
        "Drove alignment across four teams",
        "Cut deploy time by 30%",
    ]


# ── GET /summaries ─────────────────────────────────────────────────────────────

async def test_list_summaries_empty(client: AsyncClient):
    r = await client.get("/summaries")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_summaries_returns_created(client: AsyncClient):
    await _seed_entry(client, "work", "2025-03-12")

    with _mock_llm("text"):
        await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)

    r = await client.get("/summaries")
    assert len(r.json()) == 1


async def test_list_summaries_filter_by_summary_type(client: AsyncClient):
    await _seed_entry(client, "work", "2025-03-12")

    with _mock_llm("reflection text"):
        await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)

    with _mock_llm("perf text"):
        await client.post("/summaries/generate", json={**WEEKLY_PAYLOAD, "summary_type": "perf_review"})

    r = await client.get("/summaries", params={"summary_type": "reflection"})
    body = r.json()
    assert len(body) == 1
    assert body[0]["summary_type"] == "reflection"


async def test_list_summaries_filter_by_period_type(client: AsyncClient):
    await _seed_entry(client, "work", "2025-03-12")

    with _mock_llm("weekly text"):
        await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)

    monthly_payload = {
        "period_type": "monthly",
        "start_date": "2025-03-01",
        "end_date": "2025-03-31",
        "summary_type": "reflection",
    }
    with _mock_llm("monthly text"):
        await client.post("/summaries/generate", json=monthly_payload)

    r = await client.get("/summaries", params={"period_type": "monthly"})
    body = r.json()
    assert len(body) == 1
    assert body[0]["period_type"] == "monthly"


# ── GET /summaries/{id} ────────────────────────────────────────────────────────

async def test_get_summary_by_id(client: AsyncClient):
    await _seed_entry(client, "work", "2025-03-12")

    with _mock_llm("text"):
        created = (await client.post("/summaries/generate", json=WEEKLY_PAYLOAD)).json()

    r = await client.get(f"/summaries/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_summary_not_found(client: AsyncClient):
    r = await client.get(f"/summaries/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_get_summary_invalid_uuid_returns_422(client: AsyncClient):
    r = await client.get("/summaries/not-a-uuid")
    assert r.status_code == 422
