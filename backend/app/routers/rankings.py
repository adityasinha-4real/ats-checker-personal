from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.database import Ranking, JobDescription, Analysis, Resume, get_db
from app.models.schemas import RankingResponse, JobDescriptionListItem, RankingItem

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/{jd_id}", response_model=RankingResponse)
async def get_rankings(jd_id: int, db: AsyncSession = Depends(get_db)):
    jd_result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = jd_result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    result = await db.execute(
        select(Ranking)
        .options(
            selectinload(Ranking.resume),
            selectinload(Ranking.analysis),
        )
        .where(Ranking.jd_id == jd_id)
        .order_by(Ranking.rank.asc())
    )
    rankings = result.scalars().all()

    return RankingResponse(
        job_description=JobDescriptionListItem(
            id=jd.id,
            title=jd.title,
            company=jd.company,
            created_at=jd.created_at,
        ),
        rankings=rankings,
        total=len(rankings),
    )
