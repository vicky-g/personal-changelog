import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.exceptions import NoEntriesFound, SummaryNotFound
from app.models import PeriodType, SummaryType
from app.schemas import SummaryCreate, SummaryResponse
from app.services.summary_service import SummaryService

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.post("/generate", response_model=SummaryResponse, status_code=status.HTTP_201_CREATED)
async def generate_summary(
    body: SummaryCreate,
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    service = SummaryService(session)
    try:
        summary = await service.generate(
            period_type=body.period_type,
            start_date=body.start_date,
            end_date=body.end_date,
            summary_type=body.summary_type,
        )
    except NoEntriesFound as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return SummaryResponse.model_validate(summary)


@router.get("", response_model=list[SummaryResponse])
async def list_summaries(
    period_type: Optional[PeriodType] = Query(None),
    summary_type: Optional[SummaryType] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[SummaryResponse]:
    service = SummaryService(session)
    summaries = await service.list_summaries(
        period_type=period_type,
        summary_type=summary_type,
        limit=limit,
        offset=offset,
    )
    return [SummaryResponse.model_validate(s) for s in summaries]


@router.get("/{summary_id}", response_model=SummaryResponse)
async def get_summary(
    summary_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    service = SummaryService(session)
    try:
        summary = await service.get(summary_id)
    except SummaryNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")
    return SummaryResponse.model_validate(summary)
