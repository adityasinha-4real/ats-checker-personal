from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.database import Analysis, Resume, JobDescription, Ranking, get_db
from app.models.schemas import (
    AnalysisRequest, BulkAnalysisRequest, AnalysisResponse,
    AnalysisListItem, DashboardStats,
)
from app.services.ats_scorer import run_ats_analysis
from app.services.nlp_engine import extract_jd_keywords, extract_skills_from_text

router = APIRouter(prefix="/analysis", tags=["analysis"])


async def _get_or_create_jd(db: AsyncSession, request_jd_id: int | None, jd_text: str | None, jd_title: str, jd_company: str) -> JobDescription:
    if request_jd_id:
        result = await db.execute(select(JobDescription).where(JobDescription.id == request_jd_id))
        jd = result.scalar_one_or_none()
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        return jd

    if not jd_text:
        raise HTTPException(status_code=400, detail="Either jd_id or jd_text is required")

    keywords = extract_jd_keywords(jd_text)
    skills = extract_skills_from_text(jd_text)
    jd = JobDescription(
        title=jd_title,
        company=jd_company,
        description=jd_text,
        parsed_data={"keywords": keywords, "skills": skills, "keyword_count": len(keywords)},
    )
    db.add(jd)
    await db.flush()
    return jd


async def _run_single_analysis(db: AsyncSession, resume: Resume, jd: JobDescription) -> Analysis:
    resume_data = resume.parsed_data or {}
    resume_data["raw_text"] = resume.raw_text or ""

    results = run_ats_analysis(resume_data, jd.description)

    analysis = Analysis(
        resume_id=resume.id,
        jd_id=jd.id,
        **{k: results[k] for k in [
            "overall_score", "keyword_score", "skills_score",
            "experience_score", "education_score", "semantic_score",
            "missing_keywords", "missing_skills", "matched_keywords",
            "matched_skills", "suggestions", "details",
        ]},
    )
    db.add(analysis)
    await db.flush()

    result_r = await db.execute(
        select(Ranking).where(Ranking.jd_id == jd.id, Ranking.resume_id == resume.id)
    )
    ranking = result_r.scalar_one_or_none()
    if ranking:
        ranking.overall_score = results["overall_score"]
        ranking.analysis_id = analysis.id
    else:
        ranking = Ranking(
            jd_id=jd.id,
            resume_id=resume.id,
            analysis_id=analysis.id,
            overall_score=results["overall_score"],
        )
        db.add(ranking)

    await db.flush()
    return analysis


async def _rerank(db: AsyncSession, jd_id: int):
    """Update rank column for all resumes in a JD."""
    result = await db.execute(
        select(Ranking).where(Ranking.jd_id == jd_id).order_by(Ranking.overall_score.desc())
    )
    rankings = result.scalars().all()
    for i, r in enumerate(rankings, 1):
        r.rank = i


@router.post("/run", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def run_analysis(request: AnalysisRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    jd = await _get_or_create_jd(db, request.jd_id, request.jd_text, request.jd_title, request.jd_company)
    analysis = await _run_single_analysis(db, resume, jd)
    await _rerank(db, jd.id)
    await db.flush()

    result2 = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.resume), selectinload(Analysis.job_description))
        .where(Analysis.id == analysis.id)
    )
    return result2.scalar_one()


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_analysis(request: BulkAnalysisRequest, db: AsyncSession = Depends(get_db)):
    if not request.resume_ids:
        raise HTTPException(status_code=400, detail="No resume IDs provided")

    jd = await _get_or_create_jd(db, request.jd_id, request.jd_text, request.jd_title, request.jd_company)
    analyses = []

    for resume_id in request.resume_ids:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if not resume:
            logger.warning(f"Resume {resume_id} not found, skipping")
            continue
        analysis = await _run_single_analysis(db, resume, jd)
        analyses.append({"resume_id": resume_id, "analysis_id": analysis.id, "score": analysis.overall_score})

    await _rerank(db, jd.id)
    return {"jd_id": jd.id, "analyses": analyses, "total": len(analyses)}


@router.get("", response_model=list[AnalysisListItem])
async def list_analyses(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.resume), selectinload(Analysis.job_description))
        .order_by(Analysis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    total_resumes = (await db.execute(select(func.count(Resume.id)))).scalar_one()
    total_jds = (await db.execute(select(func.count(JobDescription.id)))).scalar_one()
    total_analyses = (await db.execute(select(func.count(Analysis.id)))).scalar_one()

    avg_result = await db.execute(select(func.avg(Analysis.overall_score)))
    avg_score = avg_result.scalar_one() or 0.0

    top_result = await db.execute(select(func.max(Analysis.overall_score)))
    top_score = top_result.scalar_one() or 0.0

    recent_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.resume), selectinload(Analysis.job_description))
        .order_by(Analysis.created_at.desc())
        .limit(5)
    )
    recent = recent_result.scalars().all()

    return DashboardStats(
        total_resumes=total_resumes,
        total_jds=total_jds,
        total_analyses=total_analyses,
        avg_score=round(avg_score, 1),
        top_score=round(top_score, 1),
        recent_analyses=recent,
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.resume), selectinload(Analysis.job_description))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await db.execute(delete(Analysis).where(Analysis.id == analysis_id))
