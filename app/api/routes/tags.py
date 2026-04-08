from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models import EntryType
from app.schemas import TagsPage
from app.services.entry_service import EntryService

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagsPage)
async def list_tags(
    entry_type: Optional[EntryType] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> TagsPage:
    service = EntryService(session)
    items, total = await service.list_tags(entry_type, limit=limit, offset=offset)
    return TagsPage(items=items, total=total)
