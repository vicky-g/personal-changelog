import enum
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, DateTime, Enum as SQLEnum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EntryType(str, enum.Enum):
    glow = "glow"
    grow = "grow"


class PeriodType(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


class SummaryType(str, enum.Enum):
    reflection = "reflection"
    perf_review = "perf_review"
    opportunities = "opportunities"


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_type: Mapped[EntryType] = mapped_column(SQLEnum(EntryType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    @property
    def is_editable(self) -> bool:
        if self.created_at is None:
            return True
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created > cutoff

    def __repr__(self) -> str:
        return f"<Entry id={self.id} type={self.entry_type} date={self.date}>"


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    period_type: Mapped[PeriodType] = mapped_column(SQLEnum(PeriodType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_bullets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_type: Mapped[SummaryType] = mapped_column(SQLEnum(SummaryType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Summary id={self.id} period={self.period_type} type={self.summary_type}>"
