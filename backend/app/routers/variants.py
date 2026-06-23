"""
Variants Router — Feature 3: Multi-Resume Management.
CRUD for resume variants + best-fit recommendation.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.database import Resume, JobDescription, ResumeVariant, get_db
from app.services.nlp_engine import extract_skills_from_text

router = APIRouter(prefix="/variants", tags=["variants"])

_VALID_TYPES = {"master", "backend", "fullstack", "ai", "custom"}


# ── Request / response models ─────────────────────────────────────────────────

class VariantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    variant_type: str = Field(default="custom")
    resume_id: int | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class VariantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    content: dict[str, Any] | None = None
    variant_type: str | None = None


class VariantRecommendRequest(BaseModel):
    jd_id: int | None = None
    jd_text: str | None = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_dict(v: ResumeVariant) -> dict:
    return {
        "id": v.id,
        "name": v.name,
        "variant_type": v.variant_type,
        "resume_id": v.resume_id,
        "content": v.content or {},
        "description": v.description or "",
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
    }


def _skills_from_content(content: dict) -> list[str]:
    """Extract skill list from a variant content dict."""
    skills_obj = content.get("skills", {})
    if isinstance(skills_obj, dict):
        return skills_obj.get("all", [])
    if isinstance(skills_obj, list):
        return skills_obj
    return []


def _score_variant_for_jd(variant_skills: list[str], jd_skills: list[str]) -> float:
    """Simple Jaccard overlap score for variant vs JD."""
    if not jd_skills:
        return 0.0
    v_set = {s.lower() for s in variant_skills}
    j_set = {s.lower() for s in jd_skills}
    if not j_set:
        return 0.0
    intersection = len(v_set & j_set)
    return round(intersection / len(j_set) * 100, 1)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_variant(body: VariantCreate, db: AsyncSession = Depends(get_db)):
    """Create a new resume variant."""
    if body.variant_type not in _VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"variant_type must be one of {sorted(_VALID_TYPES)}")
    if body.resume_id:
        res = await db.execute(select(Resume).where(Resume.id == body.resume_id))
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Base resume not found")
    v = ResumeVariant(
        name=body.name,
        variant_type=body.variant_type,
        resume_id=body.resume_id,
        content=body.content,
        description=body.description,
    )
    db.add(v)
    await db.flush()
    await db.refresh(v)
    return _to_dict(v)


@router.get("")
async def list_variants(db: AsyncSession = Depends(get_db)):
    """List all resume variants."""
    result = await db.execute(select(ResumeVariant).order_by(ResumeVariant.created_at.desc()))
    return [_to_dict(v) for v in result.scalars().all()]


@router.get("/{variant_id}")
async def get_variant(variant_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single variant."""
    result = await db.execute(select(ResumeVariant).where(ResumeVariant.id == variant_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Variant not found")
    return _to_dict(v)


@router.put("/{variant_id}")
async def update_variant(variant_id: int, body: VariantUpdate, db: AsyncSession = Depends(get_db)):
    """Update variant name, description, content, or type."""
    result = await db.execute(select(ResumeVariant).where(ResumeVariant.id == variant_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Variant not found")
    if body.name is not None:
        v.name = body.name
    if body.description is not None:
        v.description = body.description
    if body.content is not None:
        v.content = body.content
    if body.variant_type is not None:
        if body.variant_type not in _VALID_TYPES:
            raise HTTPException(status_code=400, detail=f"variant_type must be one of {sorted(_VALID_TYPES)}")
        v.variant_type = body.variant_type
    await db.flush()
    await db.refresh(v)
    return _to_dict(v)


@router.delete("/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(variant_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a variant."""
    result = await db.execute(select(ResumeVariant).where(ResumeVariant.id == variant_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Variant not found")
    await db.delete(v)


@router.post("/{variant_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_variant(variant_id: int, db: AsyncSession = Depends(get_db)):
    """Duplicate an existing variant."""
    result = await db.execute(select(ResumeVariant).where(ResumeVariant.id == variant_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Variant not found")
    copy = ResumeVariant(
        name=f"{v.name} (copy)",
        variant_type=v.variant_type,
        resume_id=v.resume_id,
        content=dict(v.content or {}),
        description=v.description or "",
    )
    db.add(copy)
    await db.flush()
    await db.refresh(copy)
    return _to_dict(copy)


@router.post("/recommend")
async def recommend_variant(body: VariantRecommendRequest, db: AsyncSession = Depends(get_db)):
    """Return the variant that best matches the given JD."""
    # Resolve JD text
    jd_text = ""
    if body.jd_id:
        res = await db.execute(select(JobDescription).where(JobDescription.id == body.jd_id))
        jd = res.scalar_one_or_none()
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        jd_text = jd.description
    elif body.jd_text:
        jd_text = body.jd_text
    else:
        raise HTTPException(status_code=400, detail="Either jd_id or jd_text is required")

    jd_skills = extract_skills_from_text(jd_text)

    result = await db.execute(select(ResumeVariant).order_by(ResumeVariant.created_at.desc()))
    variants = result.scalars().all()
    if not variants:
        raise HTTPException(status_code=404, detail="No variants found")

    scored = []
    for v in variants:
        skills = _skills_from_content(v.content or {})
        score = _score_variant_for_jd(skills, jd_skills)
        scored.append({"variant": _to_dict(v), "match_score": score})

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    best = scored[0]

    return {
        "recommended": best["variant"],
        "match_score": best["match_score"],
        "all_scores": [{"id": s["variant"]["id"], "name": s["variant"]["name"], "score": s["match_score"]} for s in scored],
        "reasoning": (
            f"Variant '{best['variant']['name']}' has the highest skills overlap "
            f"({best['match_score']:.0f}%) with this job description."
        ),
    }
