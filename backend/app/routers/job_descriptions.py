from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from loguru import logger

from app.models.database import JobDescription, get_db
from app.models.schemas import (
    JobDescriptionCreate, JobDescriptionUpdate,
    JobDescriptionResponse, JobDescriptionListItem,
)
from app.services.nlp_engine import extract_jd_keywords, extract_skills_from_text

router = APIRouter(prefix="/job-descriptions", tags=["job-descriptions"])


@router.post("", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_jd(data: JobDescriptionCreate, db: AsyncSession = Depends(get_db)):
    keywords = extract_jd_keywords(data.description)
    skills = extract_skills_from_text(data.description)
    parsed_data = {"keywords": keywords, "skills": skills, "keyword_count": len(keywords)}

    jd = JobDescription(
        title=data.title,
        company=data.company,
        description=data.description,
        parsed_data=parsed_data,
    )
    db.add(jd)
    await db.flush()
    await db.refresh(jd)
    return jd


@router.get("", response_model=list[JobDescriptionListItem])
async def list_jds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobDescription).order_by(JobDescription.created_at.desc()))
    return result.scalars().all()


@router.get("/{jd_id}", response_model=JobDescriptionResponse)
async def get_jd(jd_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    return jd


@router.put("/{jd_id}", response_model=JobDescriptionResponse)
async def update_jd(jd_id: int, data: JobDescriptionUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    if data.title is not None:
        jd.title = data.title
    if data.company is not None:
        jd.company = data.company
    if data.description is not None:
        jd.description = data.description
        keywords = extract_jd_keywords(data.description)
        skills = extract_skills_from_text(data.description)
        jd.parsed_data = {"keywords": keywords, "skills": skills, "keyword_count": len(keywords)}

    await db.flush()
    await db.refresh(jd)
    return jd


@router.delete("/{jd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jd(jd_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    await db.execute(delete(JobDescription).where(JobDescription.id == jd_id))
