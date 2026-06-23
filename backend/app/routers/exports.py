from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.database import Analysis, Ranking, JobDescription, Resume, get_db
from app.services.export_service import generate_pdf_report, generate_csv_ranking

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/pdf/{analysis_id}")
async def export_pdf(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.resume), selectinload(Analysis.job_description))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_dict = {
        "overall_score": analysis.overall_score,
        "keyword_score": analysis.keyword_score,
        "skills_score": analysis.skills_score,
        "experience_score": analysis.experience_score,
        "education_score": analysis.education_score,
        "semantic_score": analysis.semantic_score,
        "missing_keywords": analysis.missing_keywords or [],
        "missing_skills": analysis.missing_skills or [],
        "matched_skills": analysis.matched_skills or [],
        "suggestions": analysis.suggestions or [],
    }
    resume_dict = {
        "original_filename": analysis.resume.original_filename if analysis.resume else "N/A",
        "parsed_data": analysis.resume.parsed_data if analysis.resume else {},
    }
    jd_dict = {
        "title": analysis.job_description.title if analysis.job_description else "N/A",
        "company": analysis.job_description.company if analysis.job_description else "",
    }

    pdf_bytes = generate_pdf_report(analysis_dict, resume_dict, jd_dict)

    filename = f"ats_report_{analysis_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/csv/{jd_id}")
async def export_csv(jd_id: int, db: AsyncSession = Depends(get_db)):
    jd_result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = jd_result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    result = await db.execute(
        select(Ranking)
        .options(selectinload(Ranking.resume), selectinload(Ranking.analysis))
        .where(Ranking.jd_id == jd_id)
        .order_by(Ranking.rank.asc())
    )
    rankings = result.scalars().all()

    rankings_list = []
    for r in rankings:
        analysis = r.analysis
        resume = r.resume
        analysis_dict = {}
        if analysis:
            analysis_dict = {
                "keyword_score": analysis.keyword_score,
                "skills_score": analysis.skills_score,
                "experience_score": analysis.experience_score,
                "education_score": analysis.education_score,
                "semantic_score": analysis.semantic_score,
                "matched_skills": analysis.matched_skills or [],
                "missing_skills": analysis.missing_skills or [],
            }
        resume_dict = {}
        if resume:
            resume_dict = {
                "original_filename": resume.original_filename,
                "parsed_data": resume.parsed_data or {},
            }
        rankings_list.append({
            "rank": r.rank,
            "overall_score": r.overall_score,
            "resume": resume_dict,
            "analysis": analysis_dict,
        })

    csv_bytes = generate_csv_ranking(rankings_list, {"title": jd.title, "company": jd.company})

    filename = f"rankings_{jd_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
