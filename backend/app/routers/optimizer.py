"""
Optimizer Router — Features 1, 2, 4, 5 + Company-Specific Variant Save + Cover Letter.
POST /api/optimizer/generate         → full optimization report.
POST /api/optimizer/export/docx      → DOCX download.
POST /api/optimizer/export/pdf       → PDF download.
POST /api/optimizer/save-as-variant  → persist optimized resume as a named variant.
POST /api/optimizer/cover-letter     → generate cover letter from resume + JD.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.database import Resume, JobDescription, ResumeVariant, get_db
from app.models.schemas import IntelligenceRequest
from app.services.ats_scorer import run_ats_analysis
from app.services.jd_intelligence import classify_jd
from app.services.gap_analyzer import analyze_gaps
from app.services.rewrite_engine import generate_all_rewrites
from app.services.project_analyzer import analyze_project_relevance
from app.services.quality_audit import audit_resume
from app.services.resume_optimizer import generate_optimized_resume
from app.services.resume_diff import generate_diff
from app.services.interview_probability import compute_interview_probability
from app.services.competitiveness import analyze_competitiveness
from app.services.resume_exporter import export_to_docx, export_to_pdf
from app.services.cover_letter import generate_cover_letter
from app.services.nlp_engine import extract_jd_keywords, extract_skills_from_text

router = APIRouter(prefix="/optimizer", tags=["optimizer"])


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
    kws = extract_jd_keywords(jd_text)
    skills = extract_skills_from_text(jd_text)
    jd = JobDescription(
        title=jd_title, company=jd_company, description=jd_text,
        parsed_data={"keywords": kws, "skills": skills},
    )
    db.add(jd)
    await db.flush()
    return jd


@router.post("/generate", status_code=status.HTTP_200_OK)
async def generate_optimization(
    request: IntelligenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Full optimization pipeline: optimized resume + diff + interview probability + competitiveness.
    Does NOT persist an analysis record (use /intelligence/analyze for that).
    """
    res = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    resume = res.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    jd = await _resolve_jd(db, request.jd_id, request.jd_text, request.jd_title, request.jd_company)

    resume_data: dict = resume.parsed_data or {}
    resume_data["raw_text"] = resume.raw_text or ""
    fresher_mode = request.mode == "fresher"

    jd_intel = classify_jd(jd.description)
    ats_result = run_ats_analysis(resume_data, jd.description, fresher_mode=fresher_mode)
    gap = analyze_gaps(resume_data, jd_intel, ats_result)
    rewrites = generate_all_rewrites(resume_data, gap)
    proj_rel = analyze_project_relevance(resume_data, jd.description)
    quality = audit_resume(resume_data)

    optimized = generate_optimized_resume(resume_data, jd.description, jd_intel, gap, proj_rel, rewrites)
    diff = generate_diff(resume_data, optimized)
    interview_prob = compute_interview_probability(ats_result, gap, proj_rel, quality)
    competitiveness = analyze_competitiveness(ats_result, gap, proj_rel)

    return {
        "resume_id": resume.id,
        "jd_id": jd.id,
        "mode": request.mode,
        "ats_score": ats_result,
        "optimized_resume": optimized,
        "diff": diff,
        "interview_probability": interview_prob,
        "competitiveness": competitiveness,
    }


@router.post("/export/docx")
async def export_docx_endpoint(optimized: dict[str, Any] = Body(...)):
    """Accept an optimized resume dict and return a DOCX file."""
    try:
        data = export_to_docx(optimized)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="optimized_resume.docx"'},
        )
    except Exception as e:
        logger.error(f"DOCX export error: {e}")
        raise HTTPException(status_code=500, detail=f"DOCX export failed: {e}")


@router.post("/export/pdf")
async def export_pdf_endpoint(optimized: dict[str, Any] = Body(...)):
    """Accept an optimized resume dict and return a PDF file."""
    try:
        data = export_to_pdf(optimized)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="optimized_resume.pdf"'},
        )
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {e}")


# ── Feature 2: Company-Specific Resume Variant Save ───────────────────────────

class SaveAsVariantRequest(BaseModel):
    optimized_resume: dict[str, Any]
    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    date: str = Field(default="")


@router.post("/save-as-variant", status_code=status.HTTP_201_CREATED)
async def save_as_variant(body: SaveAsVariantRequest, db: AsyncSession = Depends(get_db)):
    """
    Persist an optimized resume as a named ResumeVariant.
    Auto-names the variant as Company_Role_Date.
    """
    date_str = body.date or date.today().isoformat()
    # Sanitise for use in a filename-style name
    safe_company = body.company.replace(" ", "_").replace("/", "-")
    safe_role = body.role.replace(" ", "_").replace("/", "-")
    variant_name = f"{safe_company}_{safe_role}_{date_str}"

    variant = ResumeVariant(
        name=variant_name,
        variant_type="custom",
        content=body.optimized_resume,
        description=f"Optimized for {body.role} at {body.company} on {date_str}",
    )
    db.add(variant)
    await db.flush()
    await db.refresh(variant)

    return {
        "id": variant.id,
        "name": variant.name,
        "variant_type": variant.variant_type,
        "resume_id": variant.resume_id,
        "content": variant.content,
        "description": variant.description,
        "created_at": variant.created_at.isoformat() if variant.created_at else None,
        "updated_at": variant.updated_at.isoformat() if variant.updated_at else None,
    }


# ── Feature 3: Cover Letter Generator ────────────────────────────────────────

class CoverLetterRequest(BaseModel):
    resume_id: int
    jd_id: int | None = None
    jd_text: str | None = None
    company: str = Field(default="the company")
    mode: str = Field(default="experienced", pattern="^(fresher|experienced)$")


@router.post("/cover-letter")
async def generate_cover_letter_endpoint(
    request: CoverLetterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a cover letter from resume content + JD.
    Never fabricates experience or skills.
    """
    res = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    resume = res.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    jd_text = ""
    jd_intel = None
    if request.jd_id:
        result = await db.execute(select(JobDescription).where(JobDescription.id == request.jd_id))
        jd = result.scalar_one_or_none()
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        jd_text = jd.description
        jd_intel = classify_jd(jd_text)
    elif request.jd_text:
        jd_text = request.jd_text
        jd_intel = classify_jd(jd_text)
    else:
        raise HTTPException(status_code=400, detail="Either jd_id or jd_text is required")

    resume_data: dict = resume.parsed_data or {}
    resume_data["raw_text"] = resume.raw_text or ""

    result = generate_cover_letter(
        resume_data=resume_data,
        jd_text=jd_text,
        company_name=request.company,
        jd_intelligence=jd_intel,
        mode=request.mode,
    )
    return result
