import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.exceptions import EntryNotEditable, EntryNotFound
from app.schemas import EntryCreate, EntryResponse, EntryUpdate
from app.services.entry_service import EntryService

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: EntryCreate,
    session: AsyncSession = Depends(get_session),
) -> EntryResponse:
    service = EntryService(session)
    entry = await service.create(body)
    return EntryResponse.model_validate(entry)


@router.get("", response_model=list[EntryResponse])
async def list_entries(
    entry_date: Optional[date] = Query(None, alias="date"),
    tag: list[str] = Query(default=[]),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[EntryResponse]:
    service = EntryService(session)
    entries = await service.list_entries(
        date=entry_date, tags=tag or None, limit=limit, offset=offset
    )
    return [EntryResponse.model_validate(e) for e in entries]


@router.get("/search", response_model=list[EntryResponse])
async def search_entries(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session),
) -> list[EntryResponse]:
    service = EntryService(session)
    entries = await service.search(q)
    return [EntryResponse.model_validate(e) for e in entries]


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> EntryResponse:
    service = EntryService(session)
    try:
        entry = await service.get(entry_id)
    except EntryNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return EntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: uuid.UUID,
    body: EntryUpdate,
    session: AsyncSession = Depends(get_session),
) -> EntryResponse:
    service = EntryService(session)
    try:
        entry = await service.update(entry_id, body)
    except EntryNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    except EntryNotEditable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Entry is no longer editable (created more than 24 hours ago)",
        )
    return EntryResponse.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    service = EntryService(session)
    try:
        await service.delete(entry_id)
    except EntryNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
