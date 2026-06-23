"""
Intelligence Router — Phase 9.
POST /api/intelligence/analyze  →  full tailoring report.
GET  /api/intelligence/jd/{jd_id}  →  JD classification only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.database import Resume, JobDescription, Analysis, Ranking, get_db
from app.models.schemas import (
    IntelligenceRequest,
    TailoringReportResponse,
    JDIntelligenceResult,
    AnalysisResponse,
)
from app.services.ats_scorer import run_ats_analysis
from app.services.jd_intelligence import classify_jd
from app.services.gap_analyzer import analyze_gaps
from app.services.rewrite_engine import generate_all_rewrites
from app.services.project_analyzer import analyze_project_relevance
from app.services.recruiter_view import generate_recruiter_view
from app.services.quality_audit import audit_resume
from app.services.nlp_engine import extract_jd_keywords, extract_skills_from_text

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


async def _resolve_jd(
    db: AsyncSession,
    jd_id: int | None,
    jd_text: str | None,
    jd_title: str,
    jd_company: str,
) -> JobDescription:
    if jd_id:
        result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
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
        parsed_data={"keywords": keywords, "skills": skills},
    )
    db.add(jd)
    await db.flush()
    return jd


async def _persist_analysis(
    db: AsyncSession,
    resume: Resume,
    jd: JobDescription,
    ats_result: dict,
) -> Analysis:
    """Save the ATS result to the analyses table and update ranking."""
    analysis = Analysis(
        resume_id=resume.id,
        jd_id=jd.id,
        **{k: ats_result[k] for k in [
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
        ranking.overall_score = ats_result["overall_score"]
        ranking.analysis_id = analysis.id
    else:
        ranking = Ranking(
            jd_id=jd.id,
            resume_id=resume.id,
            analysis_id=analysis.id,
            overall_score=ats_result["overall_score"],
            rank=1,
        )
        db.add(ranking)
    await db.flush()
    return analysis


@router.post(
    "/analyze",
    status_code=status.HTTP_201_CREATED,
)
async def full_analyze(
    request: IntelligenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the full tailoring-report pipeline for one resume vs one JD.

    Saves the base ATS analysis to history (same as /analysis/run).
    Returns the extended tailoring report in addition to the ATS scores.
    """
    # ── Load resume ──────────────────────────────────────────────────────────
    result = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # ── Resolve / create JD ───────────────────────────────────────────────────
    jd = await _resolve_jd(db, request.jd_id, request.jd_text, request.jd_title, request.jd_company)

    resume_data: dict = resume.parsed_data or {}
    resume_data["raw_text"] = resume.raw_text or ""

    fresher_mode = request.mode == "fresher"

    # ── Phase 1: JD Intelligence ─────────────────────────────────────────────
    logger.debug("Running JD intelligence classification")
    jd_intel = classify_jd(jd.description)

    # ── Phase 5 / ATS scoring (with fresher flag) ────────────────────────────
    logger.debug(f"Running ATS analysis (mode={request.mode})")
    ats_result = run_ats_analysis(resume_data, jd.description, fresher_mode=fresher_mode)

    # ── Persist to DB so it appears in history ────────────────────────────────
    analysis_orm = await _persist_analysis(db, resume, jd, ats_result)

    # Load back with relationships for the response
    result2 = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.resume), selectinload(Analysis.job_description))
        .where(Analysis.id == analysis_orm.id)
    )
    analysis_with_rels = result2.scalar_one()

    # ── Phase 2: Gap Analysis ─────────────────────────────────────────────────
    logger.debug("Running gap analysis")
    gap = analyze_gaps(resume_data, jd_intel, ats_result)

    # ── Phase 3: Rewrites ─────────────────────────────────────────────────────
    logger.debug("Generating rewrite suggestions")
    rewrites = generate_all_rewrites(resume_data, gap)

    # ── Phase 4: Project Relevance ────────────────────────────────────────────
    logger.debug("Analysing project relevance")
    proj_rel = analyze_project_relevance(resume_data, jd.description)

    # ── Phase 8: Quality Audit ────────────────────────────────────────────────
    logger.debug("Running quality audit")
    quality = audit_resume(resume_data)

    # ── Phase 6: Recruiter View ───────────────────────────────────────────────
    logger.debug("Generating recruiter view")
    recruiter = generate_recruiter_view(resume_data, ats_result, jd_intel, gap, quality)

    return {
        "resume_id": resume.id,
        "jd_id": jd.id,
        "mode": request.mode,
        "ats_score": analysis_with_rels,
        "jd_intelligence": jd_intel,
        "gap_analysis": gap,
        "rewrites": rewrites,
        "project_relevance": proj_rel,
        "recruiter_view": recruiter,
        "quality_audit": quality,
    }


@router.get("/jd/{jd_id}", response_model=JDIntelligenceResult)
async def get_jd_intelligence(jd_id: int, db: AsyncSession = Depends(get_db)):
    """Classify an already-stored JD and return structured intelligence."""
    result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    return classify_jd(jd.description)
