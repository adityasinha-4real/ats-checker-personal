"""
Market Analyzer Router — Feature 6 + Skill Gap Roadmap.
POST /api/market/analyze  → aggregate skill demand across multiple JDs.
POST /api/market/roadmap  → phased learning plan from missing skills.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import Resume, JobDescription, get_db
from app.services.market_analyzer import analyze_market
from app.services.skill_roadmap import generate_roadmap

router = APIRouter(prefix="/market", tags=["market"])


class MarketAnalysisRequest(BaseModel):
    jd_texts: list[str] = Field(default_factory=list, description="Raw JD text strings")
    jd_ids: list[int] = Field(default_factory=list, description="IDs of saved JDs to include")
    resume_id: int | None = Field(default=None, description="Resume to compare profile against")


@router.post("/analyze")
async def analyze_market_endpoint(
    body: MarketAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze multiple job descriptions to surface the most in-demand skills.
    Optionally compare against a resume to highlight profile gaps.
    """
    jd_texts = list(body.jd_texts)

    # Load saved JDs from DB
    if body.jd_ids:
        result = await db.execute(
            select(JobDescription).where(JobDescription.id.in_(body.jd_ids))
        )
        for jd in result.scalars().all():
            jd_texts.append(jd.description)

    if not jd_texts:
        raise HTTPException(status_code=400, detail="Provide at least one JD (jd_texts or jd_ids)")

    # Load resume skills if requested
    resume_skills: list[str] | None = None
    if body.resume_id:
        res = await db.execute(select(Resume).where(Resume.id == body.resume_id))
        resume = res.scalar_one_or_none()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        parsed = resume.parsed_data or {}
        resume_skills = parsed.get("skills", [])

    return analyze_market(jd_texts, resume_skills)


# ── Skill Gap Roadmap ─────────────────────────────────────────────────────────

class RoadmapRequest(BaseModel):
    missing_skills: list[dict] = Field(
        default_factory=list,
        description="List of missing skill entries from market analysis (skill, count, percentage, category)"
    )
    resume_id: int | None = None


@router.post("/roadmap")
async def generate_roadmap_endpoint(
    body: RoadmapRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Produce a phased skill learning roadmap from market gap analysis.
    Provide missing_skills from /market/analyze missing_from_profile.
    """
    if not body.missing_skills:
        raise HTTPException(status_code=400, detail="missing_skills list cannot be empty")

    resume_skills: list[str] | None = None
    if body.resume_id:
        res = await db.execute(select(Resume).where(Resume.id == body.resume_id))
        resume = res.scalar_one_or_none()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        parsed = resume.parsed_data or {}
        resume_skills = parsed.get("skills", [])

    return generate_roadmap(
        missing_skills=body.missing_skills,
        resume_skills=resume_skills,
    )
