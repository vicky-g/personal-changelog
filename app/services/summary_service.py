from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoEntriesFound, SummaryNotFound
from app.models import Entry, PeriodType, Summary, SummaryType
from app.prompts import (
    OPPORTUNITIES_SYSTEM,
    OPPORTUNITIES_USER,
    PERF_REVIEW_SYSTEM,
    PERF_REVIEW_USER,
    REFLECTION_SYSTEM,
    REFLECTION_USER,
)
from app.services.entry_service import EntryService
from app.services.llm_client import LLMClient


_PROMPTS: dict[SummaryType, tuple[str, str]] = {
    SummaryType.reflection: (REFLECTION_SYSTEM, REFLECTION_USER),
    SummaryType.perf_review: (PERF_REVIEW_SYSTEM, PERF_REVIEW_USER),
    SummaryType.opportunities: (OPPORTUNITIES_SYSTEM, OPPORTUNITIES_USER),
}


def _format_entries_block(entries: list[Entry]) -> str:
    lines: list[str] = []
    for entry in entries:
        tags_str = f"  [{', '.join(entry.tags)}]" if entry.tags else ""
        lines.append(f"[{entry.date}]{tags_str}\n{entry.content}")
    return "\n\n".join(lines)


def _extract_bullets(text: str) -> list[str]:
    """Pull leading-bullet lines out of generated text as raw_bullets."""
    bullets = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*", "•")) or (
            len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ".)"
        ):
            bullets.append(stripped.lstrip("-*•0123456789.) ").strip())
    return bullets


class SummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate(
        self,
        period_type: PeriodType,
        start_date: date,
        end_date: date,
        summary_type: SummaryType,
        *,
        llm_client: LLMClient | None = None,
    ) -> Summary:
        entry_service = EntryService(self.session)
        entries = await entry_service.list_entries(limit=10_000)
        entries = [e for e in entries if start_date <= e.date <= end_date]

        if not entries:
            raise NoEntriesFound(
                f"No entries found between {start_date} and {end_date}"
            )

        entries_block = _format_entries_block(entries)
        system_prompt, user_template = _PROMPTS[summary_type]
        user_prompt = user_template.format(entries_block=entries_block)

        client = llm_client or LLMClient()
        generated_text = client.complete(system=system_prompt, user=user_prompt)

        raw_bullets = _extract_bullets(generated_text)

        now = datetime.now(timezone.utc)
        summary = Summary(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            summary_type=summary_type,
            raw_bullets=raw_bullets,
            generated_text=generated_text,
            created_at=now,
        )
        self.session.add(summary)
        await self.session.flush()
        await self.session.refresh(summary)
        return summary

    async def get(self, summary_id) -> Summary:
        result = await self.session.execute(
            select(Summary).where(Summary.id == summary_id)
        )
        summary = result.scalar_one_or_none()
        if summary is None:
            raise SummaryNotFound(f"Summary {summary_id} not found")
        return summary

    async def list_summaries(
        self,
        *,
        period_type: PeriodType | None = None,
        summary_type: SummaryType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Summary]:
        stmt = select(Summary)
        if period_type is not None:
            stmt = stmt.where(Summary.period_type == period_type)
        if summary_type is not None:
            stmt = stmt.where(Summary.summary_type == summary_type)
        stmt = stmt.order_by(Summary.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
