import uuid
from datetime import date, datetime, timezone

from sqlalchemy import cast, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import EntryNotEditable, EntryNotFound
from app.models import Entry
from app.schemas import EntryCreate, EntryUpdate


def _normalize_tags(tags: list[str]) -> list[str]:
    return [tag.strip().lower() for tag in tags if tag.strip()]


class EntryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: EntryCreate) -> Entry:
        now = datetime.now(timezone.utc)
        entry = Entry(
            content=data.content,
            date=data.date,
            tags=_normalize_tags(data.tags),
            created_at=now,
            updated_at=now,
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def get(self, entry_id: uuid.UUID) -> Entry:
        result = await self.session.execute(
            select(Entry).where(Entry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            raise EntryNotFound(f"Entry {entry_id} not found")
        return entry

    async def list_entries(
        self,
        *,
        date: date | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Entry]:
        stmt = select(Entry)
        if date is not None:
            stmt = stmt.where(Entry.date == date)
        if tags:
            for tag in tags:
                normalized = tag.strip().lower()
                stmt = stmt.where(
                    cast(Entry.tags, String).ilike(f'%"{normalized}"%')
                )
        stmt = (
            stmt.order_by(Entry.date.desc(), Entry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, entry_id: uuid.UUID, data: EntryUpdate) -> Entry:
        entry = await self.get(entry_id)
        if not entry.is_editable:
            raise EntryNotEditable(
                f"Entry {entry_id} is no longer editable (created more than 24 hours ago)"
            )
        if data.content is not None:
            entry.content = data.content
        if data.tags is not None:
            entry.tags = _normalize_tags(data.tags)
        entry.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def delete(self, entry_id: uuid.UUID) -> None:
        entry = await self.get(entry_id)
        await self.session.delete(entry)
        await self.session.flush()

    async def search(self, query: str) -> list[Entry]:
        q = query.strip()
        if not q:
            return []
        stmt = (
            select(Entry)
            .where(
                or_(
                    Entry.content.ilike(f"%{q}%"),
                    cast(Entry.tags, String).ilike(f"%{q}%"),
                )
            )
            .order_by(Entry.date.desc(), Entry.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
