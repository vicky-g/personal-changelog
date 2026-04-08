"""
Tests for SummaryService.

Covers:
- Correct prompt template selected per summary_type
- Entries correctly fetched for the date range (in-range included, out-of-range excluded)
- Anthropic API call is mocked — no real requests made
- Generated text and raw_bullets saved to Summary
- NoEntriesFound raised when date range has no entries
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEntriesFound, SummaryNotFound
from app.models import PeriodType, SummaryType
from app.prompts import (
    OPPORTUNITIES_SYSTEM,
    OPPORTUNITIES_USER,
    PERF_REVIEW_SYSTEM,
    PERF_REVIEW_USER,
    REFLECTION_SYSTEM,
    REFLECTION_USER,
)
from app.models import EntryType
from app.schemas import EntryCreate
from app.services.entry_service import EntryService
from app.services.summary_service import SummaryService


# ── Helpers ────────────────────────────────────────────────────────────────────

class MockLLMClient:
    """Minimal LLMClient stand-in that records calls without hitting the API."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict] = []

    def complete(self, *, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        return self.response


async def _seed_entry(session, content: str, entry_date: date, tags=None) -> None:
    service = EntryService(session)
    await service.create(EntryCreate(entry_type=EntryType.glow, content=content, date=entry_date, tags=tags or []))


# ── Prompt template selection ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "summary_type, expected_system, expected_user",
    [
        (SummaryType.reflection, REFLECTION_SYSTEM, REFLECTION_USER),
        (SummaryType.perf_review, PERF_REVIEW_SYSTEM, PERF_REVIEW_USER),
        (SummaryType.opportunities, OPPORTUNITIES_SYSTEM, OPPORTUNITIES_USER),
    ],
)
async def test_correct_prompt_selected(
    session: AsyncSession,
    summary_type: SummaryType,
    expected_system: str,
    expected_user: str,
):
    await _seed_entry(session, "did some work", date(2025, 3, 10))
    client = MockLLMClient("Generated text.")
    service = SummaryService(session)

    await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=summary_type,
        llm_client=client,
    )

    assert len(client.calls) == 1
    assert client.calls[0]["system"] == expected_system
    assert expected_user.split("{entries_block}")[0] in client.calls[0]["user"]


# ── Date range filtering ───────────────────────────────────────────────────────

async def test_only_entries_in_range_are_included(session: AsyncSession):
    await _seed_entry(session, "before range", date(2025, 3, 1))
    await _seed_entry(session, "in range start", date(2025, 3, 10))
    await _seed_entry(session, "in range middle", date(2025, 3, 13))
    await _seed_entry(session, "in range end", date(2025, 3, 16))
    await _seed_entry(session, "after range", date(2025, 3, 20))

    client = MockLLMClient("Summary text.")
    service = SummaryService(session)

    await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=SummaryType.reflection,
        llm_client=client,
    )

    user_content = client.calls[0]["user"]
    assert "in range start" in user_content
    assert "in range middle" in user_content
    assert "in range end" in user_content
    assert "before range" not in user_content
    assert "after range" not in user_content


async def test_start_and_end_dates_are_inclusive(session: AsyncSession):
    await _seed_entry(session, "on start date", date(2025, 4, 1))
    await _seed_entry(session, "on end date", date(2025, 4, 7))

    client = MockLLMClient("Summary.")
    service = SummaryService(session)

    await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 4, 1),
        end_date=date(2025, 4, 7),
        summary_type=SummaryType.reflection,
        llm_client=client,
    )

    user_content = client.calls[0]["user"]
    assert "on start date" in user_content
    assert "on end date" in user_content


# ── NoEntriesFound ─────────────────────────────────────────────────────────────

async def test_raises_when_no_entries_in_range(session: AsyncSession):
    await _seed_entry(session, "out of range", date(2025, 1, 1))
    service = SummaryService(session)
    client = MockLLMClient("Should not be called.")

    with pytest.raises(NoEntriesFound):
        await service.generate(
            period_type=PeriodType.weekly,
            start_date=date(2025, 3, 10),
            end_date=date(2025, 3, 16),
            summary_type=SummaryType.reflection,
            llm_client=client,
        )

    assert client.calls == []


async def test_raises_when_no_entries_at_all(session: AsyncSession):
    service = SummaryService(session)
    with pytest.raises(NoEntriesFound):
        await service.generate(
            period_type=PeriodType.monthly,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31),
            summary_type=SummaryType.perf_review,
            llm_client=MockLLMClient(""),
        )


# ── Persistence ────────────────────────────────────────────────────────────────

async def test_summary_saved_with_generated_text(session: AsyncSession):
    await _seed_entry(session, "shipped auth service", date(2025, 3, 12))
    generated = "You shipped the auth service this week."
    client = MockLLMClient(generated)
    service = SummaryService(session)

    summary = await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=SummaryType.reflection,
        llm_client=client,
    )

    assert summary.id is not None
    assert summary.generated_text == generated
    assert summary.period_type == PeriodType.weekly
    assert summary.summary_type == SummaryType.reflection
    assert summary.start_date == date(2025, 3, 10)
    assert summary.end_date == date(2025, 3, 16)


async def test_raw_bullets_extracted_from_bullet_response(session: AsyncSession):
    await _seed_entry(session, "led Q1 planning", date(2025, 3, 11))
    generated = "- Led Q1 planning across three teams\n- Reduced deploy time by 40%\n- Mentored two engineers"
    client = MockLLMClient(generated)
    service = SummaryService(session)

    summary = await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=SummaryType.perf_review,
        llm_client=client,
    )

    assert summary.raw_bullets == [
        "Led Q1 planning across three teams",
        "Reduced deploy time by 40%",
        "Mentored two engineers",
    ]


async def test_raw_bullets_empty_for_prose_response(session: AsyncSession):
    await _seed_entry(session, "wrote docs", date(2025, 3, 11))
    generated = "This week you focused on documentation and communication."
    client = MockLLMClient(generated)
    service = SummaryService(session)

    summary = await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=SummaryType.reflection,
        llm_client=client,
    )

    assert summary.raw_bullets == []


# ── get / list_summaries ───────────────────────────────────────────────────────

async def test_get_returns_saved_summary(session: AsyncSession):
    await _seed_entry(session, "work", date(2025, 3, 11))
    client = MockLLMClient("text")
    service = SummaryService(session)

    created = await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=SummaryType.reflection,
        llm_client=client,
    )
    fetched = await service.get(created.id)
    assert fetched.id == created.id


async def test_get_raises_for_unknown_id(session: AsyncSession):
    service = SummaryService(session)
    with pytest.raises(SummaryNotFound):
        await service.get(uuid.uuid4())


async def test_list_summaries_filters_by_summary_type(session: AsyncSession):
    await _seed_entry(session, "work", date(2025, 3, 11))
    client_a = MockLLMClient("reflection text")
    client_b = MockLLMClient("perf text")
    service = SummaryService(session)

    await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=SummaryType.reflection,
        llm_client=client_a,
    )
    await service.generate(
        period_type=PeriodType.weekly,
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 16),
        summary_type=SummaryType.perf_review,
        llm_client=client_b,
    )

    reflections = await service.list_summaries(summary_type=SummaryType.reflection)
    assert len(reflections) == 1
    assert reflections[0].summary_type == SummaryType.reflection
