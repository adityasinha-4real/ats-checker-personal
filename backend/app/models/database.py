from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, UniqueConstraint, func
from datetime import datetime as _dt
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings


class Base(DeclarativeBase):
    pass


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    raw_text = Column(Text)
    parsed_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now(), default=_dt.utcnow)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=_dt.utcnow, default=_dt.utcnow)

    analyses = relationship("Analysis", back_populates="resume", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="resume", cascade="all, delete-orphan")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, default="")
    description = Column(Text, nullable=False)
    parsed_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now(), default=_dt.utcnow)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=_dt.utcnow, default=_dt.utcnow)

    analyses = relationship("Analysis", back_populates="job_description", cascade="all, delete-orphan")
    rankings = relationship("Ranking", back_populates="job_description", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, default=0.0)
    keyword_score = Column(Float, default=0.0)
    skills_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    education_score = Column(Float, default=0.0)
    semantic_score = Column(Float, default=0.0)
    missing_keywords = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    matched_keywords = Column(JSON, default=list)
    matched_skills = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), default=_dt.utcnow)

    resume = relationship("Resume", back_populates="analyses")
    job_description = relationship("JobDescription", back_populates="analyses")
    ranking = relationship("Ranking", back_populates="analysis", uselist=False)


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, index=True)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)
    rank = Column(Integer, default=0)
    overall_score = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now(), default=_dt.utcnow)

    __table_args__ = (UniqueConstraint("jd_id", "resume_id", name="uq_jd_resume"),)

    resume = relationship("Resume", back_populates="rankings")
    job_description = relationship("JobDescription", back_populates="rankings")
    analysis = relationship("Analysis", back_populates="ranking")


class ResumeVariant(Base):
    __tablename__ = "resume_variants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    variant_type = Column(String, default="custom")
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    content = Column(JSON, default=dict)
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    resume = relationship("Resume", foreign_keys=[resume_id])


_APP_STATUSES = {"applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"}


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    date_applied = Column(String, default="")  # YYYY-MM-DD string
    status = Column(String, default="applied")
    notes = Column(Text, default="")
    variant_id = Column(Integer, ForeignKey("resume_variants.id", ondelete="SET NULL"), nullable=True)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    variant = relationship("ResumeVariant", foreign_keys=[variant_id])
    job_description = relationship("JobDescription", foreign_keys=[jd_id])


engine = create_async_engine(settings.database_url, echo=settings.debug, connect_args={"check_same_thread": False})
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
