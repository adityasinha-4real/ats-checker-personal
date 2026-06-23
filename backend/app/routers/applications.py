"""
Application Tracker Router — Feature 1.
CRUD for job applications + aggregated analytics.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.database import Application, ResumeVariant, JobDescription, _APP_STATUSES, get_db

router = APIRouter(prefix="/applications", tags=["applications"])

_ALL_STATUSES = list(_APP_STATUSES)


# ── Request models ─────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    date_applied: str = Field(default="")
    status: str = Field(default="applied")
    notes: str = Field(default="")
    variant_id: int | None = None
    jd_id: int | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    date_applied: str | None = None
    status: str | None = None
    notes: str | None = None
    variant_id: int | None = None
    jd_id: int | None = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_dict(a: Application, variant_name: str | None = None) -> dict:
    return {
        "id": a.id,
        "company": a.company,
        "role": a.role,
        "date_applied": a.date_applied or "",
        "status": a.status,
        "notes": a.notes or "",
        "variant_id": a.variant_id,
        "jd_id": a.jd_id,
        "variant_name": variant_name,
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "updated_at": a.updated_at.isoformat() if a.updated_at else "",
    }


async def _resolve_variant_name(db: AsyncSession, variant_id: int | None) -> str | None:
    if not variant_id:
        return None
    res = await db.execute(select(ResumeVariant).where(ResumeVariant.id == variant_id))
    v = res.scalar_one_or_none()
    return v.name if v else None


# ── CRUD endpoints ─────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_application(body: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    if body.status not in _APP_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(_APP_STATUSES)}")
    if body.variant_id:
        res = await db.execute(select(ResumeVariant).where(ResumeVariant.id == body.variant_id))
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Variant not found")
    if body.jd_id:
        res = await db.execute(select(JobDescription).where(JobDescription.id == body.jd_id))
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Job description not found")

    app = Application(
        company=body.company,
        role=body.role,
        date_applied=body.date_applied,
        status=body.status,
        notes=body.notes,
        variant_id=body.variant_id,
        jd_id=body.jd_id,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    vname = await _resolve_variant_name(db, app.variant_id)
    return _to_dict(app, vname)


@router.get("")
async def list_applications(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Application).order_by(Application.created_at.desc())
    result = await db.execute(stmt)
    apps = result.scalars().all()
    if status_filter:
        apps = [a for a in apps if a.status == status_filter]

    out = []
    for a in apps:
        vname = await _resolve_variant_name(db, a.variant_id)
        out.append(_to_dict(a, vname))
    return out


@router.get("/analytics")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application))
    apps = result.scalars().all()

    total = len(apps)
    by_status: dict[str, int] = {s: 0 for s in _APP_STATUSES}
    for a in apps:
        by_status[a.status] = by_status.get(a.status, 0) + 1

    responded = sum(by_status.get(s, 0) for s in ["phone_screen", "interview", "offer", "rejected"])
    interview_count = by_status.get("interview", 0) + by_status.get("offer", 0)
    offer_count = by_status.get("offer", 0)

    conversion_rates = {
        "response_rate": round(responded / total * 100, 1) if total else 0.0,
        "interview_rate": round(interview_count / total * 100, 1) if total else 0.0,
        "offer_rate": round(offer_count / total * 100, 1) if total else 0.0,
    }

    # Variant performance
    variant_stats: dict[int, dict] = {}
    for a in apps:
        if a.variant_id:
            if a.variant_id not in variant_stats:
                variant_stats[a.variant_id] = {
                    "variant_id": a.variant_id,
                    "variant_name": None,
                    "applications": 0,
                    "interviews": 0,
                    "offers": 0,
                }
            variant_stats[a.variant_id]["applications"] += 1
            if a.status in ("interview", "offer"):
                variant_stats[a.variant_id]["interviews"] += 1
            if a.status == "offer":
                variant_stats[a.variant_id]["offers"] += 1

    for vid, stats in variant_stats.items():
        stats["variant_name"] = await _resolve_variant_name(db, vid)

    variant_performance = sorted(variant_stats.values(), key=lambda x: x["applications"], reverse=True)

    # Monthly trend (count per YYYY-MM)
    monthly: dict[str, int] = defaultdict(int)
    for a in apps:
        if a.date_applied and len(a.date_applied) >= 7:
            month_key = a.date_applied[:7]
            monthly[month_key] += 1
        elif a.created_at:
            month_key = a.created_at.strftime("%Y-%m")
            monthly[month_key] += 1

    monthly_trend = [{"month": k, "count": v} for k, v in sorted(monthly.items())]

    return {
        "total_applications": total,
        "by_status": by_status,
        "conversion_rates": conversion_rates,
        "variant_performance": variant_performance,
        "monthly_trend": monthly_trend,
    }


@router.get("/{app_id}")
async def get_application(app_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    vname = await _resolve_variant_name(db, app.variant_id)
    return _to_dict(app, vname)


@router.put("/{app_id}")
async def update_application(app_id: int, body: ApplicationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if body.status is not None and body.status not in _APP_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(_APP_STATUSES)}")
    if body.variant_id is not None:
        res = await db.execute(select(ResumeVariant).where(ResumeVariant.id == body.variant_id))
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Variant not found")
    if body.jd_id is not None:
        res = await db.execute(select(JobDescription).where(JobDescription.id == body.jd_id))
        if not res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Job description not found")

    if body.company is not None:
        app.company = body.company
    if body.role is not None:
        app.role = body.role
    if body.date_applied is not None:
        app.date_applied = body.date_applied
    if body.status is not None:
        app.status = body.status
    if body.notes is not None:
        app.notes = body.notes
    if body.variant_id is not None:
        app.variant_id = body.variant_id
    if body.jd_id is not None:
        app.jd_id = body.jd_id

    await db.flush()
    await db.refresh(app)
    vname = await _resolve_variant_name(db, app.variant_id)
    return _to_dict(app, vname)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(app_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await db.delete(app)
