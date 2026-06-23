from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import shutil
import uuid
from pathlib import Path
from loguru import logger

from app.models.database import Resume, get_db
from app.models.schemas import ResumeResponse, ResumeListItem
from app.services.resume_parser import parse_resume
from app.config import settings

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx",
}


@router.post("/upload", response_model=list[ResumeResponse], status_code=status.HTTP_201_CREATED)
async def upload_resumes(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []

    for upload_file in files:
        content_type = upload_file.content_type or ""
        extension = Path(upload_file.filename or "").suffix.lower().lstrip(".")

        file_type = ALLOWED_CONTENT_TYPES.get(content_type) or (
            extension if extension in ("pdf", "docx") else None
        )

        if not file_type:
            raise HTTPException(
                status_code=400,
                detail=f"File '{upload_file.filename}' is not a supported type (PDF or DOCX only)",
            )

        file_size = 0
        unique_name = f"{uuid.uuid4().hex}.{file_type}"
        dest_path = settings.upload_dir / unique_name

        with open(dest_path, "wb") as out:
            while chunk := await upload_file.read(8192):
                file_size += len(chunk)
                if file_size > settings.max_file_size_mb * 1024 * 1024:
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File '{upload_file.filename}' exceeds {settings.max_file_size_mb}MB limit",
                    )
                out.write(chunk)

        try:
            parsed = parse_resume(dest_path, file_type)
        except Exception as e:
            dest_path.unlink(missing_ok=True)
            logger.error(f"Parse error for {upload_file.filename}: {e}")
            raise HTTPException(status_code=422, detail=f"Could not parse '{upload_file.filename}': {e}")

        raw_text = parsed.pop("raw_text", "")
        db_resume = Resume(
            filename=unique_name,
            original_filename=upload_file.filename or unique_name,
            file_path=str(dest_path),
            file_type=file_type,
            raw_text=raw_text,
            parsed_data=parsed,
        )
        db.add(db_resume)
        await db.flush()
        await db.refresh(db_resume)
        results.append(db_resume)

    return results


@router.get("", response_model=list[ResumeListItem])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).order_by(Resume.created_at.desc()))
    return result.scalars().all()


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = Path(resume.file_path)
    file_path.unlink(missing_ok=True)

    await db.execute(delete(Resume).where(Resume.id == resume_id))
