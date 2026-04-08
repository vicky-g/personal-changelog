import uuid
from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import EntryType, PeriodType, SummaryType


# ── Entry schemas ──────────────────────────────────────────────────────────────

class EntryCreate(BaseModel):
    entry_type: EntryType
    content: str = Field(..., min_length=1)
    date: date_type = Field(default_factory=date_type.today)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        return [tag.strip().lower() for tag in v if tag.strip()]


class EntryUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)
    date: date_type | None = None
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [tag.strip().lower() for tag in v if tag.strip()]


class EntryResponse(BaseModel):
    """Full entry response — returned by POST and PATCH."""
    id: uuid.UUID
    entry_type: EntryType
    content: str
    date: date_type
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    is_editable: bool

    model_config = ConfigDict(from_attributes=True)


class EntryPublicResponse(BaseModel):
    """Slim entry response — default for GET routes. Excludes internal timestamps."""
    id: uuid.UUID
    entry_type: EntryType
    content: str
    date: date_type
    tags: list[str]
    is_editable: bool

    model_config = ConfigDict(from_attributes=True)


# ── Tag schemas ────────────────────────────────────────────────────────────────

class TagsPage(BaseModel):
    items: list[str]
    total: int


# ── Summary schemas ────────────────────────────────────────────────────────────

class SummaryCreate(BaseModel):
    period_type: PeriodType
    start_date: date_type
    end_date: date_type
    summary_type: SummaryType


class SummaryResponse(BaseModel):
    id: uuid.UUID
    period_type: PeriodType
    start_date: date_type
    end_date: date_type
    raw_bullets: list[str]
    generated_text: str | None
    summary_type: SummaryType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
