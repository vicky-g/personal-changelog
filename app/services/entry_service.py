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
            entry_type=data.entry_type,
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
        entry_type: str | None = None,
        date: date | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Entry]:
        stmt = select(Entry)
        if entry_type is not None:
            stmt = stmt.where(Entry.entry_type == entry_type)
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
        if data.entry_type is not None:
            entry.entry_type = data.entry_type
        if data.content is not None:
            entry.content = data.content
        if data.date is not None:
            entry.date = data.date
        if data.tags is not None:
            entry.tags = _normalize_tags(data.tags)
        entry.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def append_tags(self, entry_id: uuid.UUID, new_tags: list[str]) -> Entry:
        entry = await self.get(entry_id)
        normalized = _normalize_tags(new_tags)
        merged = list(dict.fromkeys(entry.tags + normalized))
        return await self.update(entry_id, EntryUpdate(tags=merged))

    async def delete(self, entry_id: uuid.UUID) -> None:
        entry = await self.get(entry_id)
        await self.session.delete(entry)
        await self.session.flush()

    async def search(self, query: str, entry_type: str | None = None) -> list[Entry]:
        q = query.strip()
        if not q:
            return []
        stmt = select(Entry).where(
            or_(
                Entry.content.ilike(f"%{q}%"),
                cast(Entry.tags, String).ilike(f"%{q}%"),
            )
        )
        if entry_type is not None:
            stmt = stmt.where(Entry.entry_type == entry_type)
        stmt = stmt.order_by(Entry.date.desc(), Entry.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_tags(
        self,
        entry_type: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[str], int]:
        stmt = select(Entry.tags)
        if entry_type is not None:
            stmt = stmt.where(Entry.entry_type == entry_type)
        result = await self.session.execute(stmt)
        all_tags: set[str] = set()
        for row in result.scalars():
            if isinstance(row, list):
                all_tags.update(row)
        sorted_tags = sorted(all_tags)
        total = len(sorted_tags)
        return sorted_tags[offset : offset + limit], total
