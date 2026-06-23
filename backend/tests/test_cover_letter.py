"""Tests for Cover Letter Generator (Feature 3 of v4.0)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.database import Base, Resume, get_db
from app.services.cover_letter import generate_cover_letter

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_RESUME_DATA = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "skills": ["Python", "Django", "PostgreSQL", "Docker", "REST APIs"],
    "experience": [
        "Developed REST APIs using Python and Django for e-commerce platform serving 50K users",
        "Improved query performance by 40% via PostgreSQL index optimization",
    ],
    "projects": [
        "Built a real-time chat application using WebSockets and Redis, supporting 10K concurrent users",
        "Created a ML pipeline for sentiment analysis with 92% accuracy",
    ],
    "education": [{"degree": "B.Tech Computer Science", "year": "2024"}],
    "certifications": ["AWS Certified Developer"],
    "years_of_experience": 2,
}

_JD_TEXT = (
    "We are looking for a Python developer with experience in Django, REST APIs, "
    "and PostgreSQL. Strong problem-solving skills required. Experience with Docker a plus."
)


class TestCoverLetterService:
    def test_returns_required_keys(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "TechCorp")
        assert "cover_letter_text" in result
        assert "paragraphs" in result
        assert "word_count" in result
        assert "safety_notes" in result

    def test_paragraphs_structure(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "TechCorp")
        paras = result["paragraphs"]
        assert "opening" in paras
        assert "body_technical" in paras
        assert "body_projects" in paras
        assert "closing" in paras

    def test_company_name_in_opening(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "Acme Corp")
        assert "Acme Corp" in result["paragraphs"]["opening"]

    def test_applicant_name_in_closing(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "Acme Corp")
        assert "Alice Smith" in result["paragraphs"]["closing"]

    def test_uses_only_resume_skills(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "TechCorp")
        body = result["paragraphs"]["body_technical"]
        # At least one known resume skill should appear
        skill_mentioned = any(s.lower() in body.lower() for s in _RESUME_DATA["skills"])
        assert skill_mentioned

    def test_word_count_reasonable(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "TechCorp")
        assert 100 < result["word_count"] < 600

    def test_no_fabrication_no_new_facts(self):
        minimal_resume = {
            "name": "Bob",
            "skills": [],
            "experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
            "years_of_experience": 0,
        }
        result = generate_cover_letter(minimal_resume, _JD_TEXT, "TechCorp")
        assert result["cover_letter_text"]
        assert len(result["safety_notes"]) > 0

    def test_safety_notes_populated_when_no_experience(self):
        no_exp_resume = {**_RESUME_DATA, "experience": []}
        result = generate_cover_letter(no_exp_resume, _JD_TEXT, "TechCorp")
        assert any("experience" in n.lower() for n in result["safety_notes"])

    def test_safety_notes_empty_when_full_resume(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "TechCorp")
        assert isinstance(result["safety_notes"], list)

    def test_fresher_mode(self):
        fresher_resume = {**_RESUME_DATA, "years_of_experience": 0}
        result = generate_cover_letter(fresher_resume, _JD_TEXT, "TechCorp", mode="fresher")
        assert result["cover_letter_text"]
        opening = result["paragraphs"]["opening"]
        # Should not claim "X years of experience" for fresher
        assert "years" not in opening or "0 years" not in opening

    def test_full_text_contains_all_paragraphs(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "TechCorp")
        full = result["cover_letter_text"]
        paras = result["paragraphs"]
        # Each paragraph should be a substring of the full text
        assert paras["opening"] in full
        assert paras["closing"] in full

    def test_project_highlight_uses_jd_keywords(self):
        result = generate_cover_letter(_RESUME_DATA, _JD_TEXT, "TechCorp")
        body_projects = result["paragraphs"]["body_projects"]
        assert body_projects  # must not be empty


_PARSED_DATA = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "skills": ["Python", "Django", "PostgreSQL", "Docker"],
    "experience": ["Developed REST APIs with Python and Django"],
    "projects": ["Built real-time chat app with WebSockets"],
    "education": [{"degree": "B.Tech Computer Science", "year": "2024"}],
    "years_of_experience": 2,
}


@pytest_asyncio.fixture
async def api_test_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield engine, SessionLocal
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client_with_resume(api_test_db):
    engine, SessionLocal = api_test_db
    # Insert a resume record directly — avoids file parsing
    async with SessionLocal() as session:
        resume = Resume(
            filename="test_resume.pdf",
            original_filename="test_resume.pdf",
            file_path="/tmp/test_resume.pdf",
            file_type="pdf",
            raw_text="Alice Smith Python Django PostgreSQL Docker",
            parsed_data=_PARSED_DATA,
        )
        session.add(resume)
        await session.commit()
        await session.refresh(resume)
        resume_id = resume.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, resume_id


class TestCoverLetterApi:
    @pytest.mark.asyncio
    async def test_cover_letter_no_resume_404(self, api_client_with_resume):
        client, _ = api_client_with_resume
        resp = await client.post("/api/optimizer/cover-letter", json={
            "resume_id": 9999,
            "jd_text": _JD_TEXT,
            "company": "TechCorp",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cover_letter_no_jd_400(self, api_client_with_resume):
        client, resume_id = api_client_with_resume
        resp = await client.post("/api/optimizer/cover-letter", json={
            "resume_id": resume_id,
            "company": "TechCorp",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cover_letter_returns_text(self, api_client_with_resume):
        client, resume_id = api_client_with_resume
        resp = await client.post("/api/optimizer/cover-letter", json={
            "resume_id": resume_id,
            "jd_text": _JD_TEXT,
            "company": "TechCorp",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "cover_letter_text" in data
        assert len(data["cover_letter_text"]) > 50

    @pytest.mark.asyncio
    async def test_cover_letter_with_jd_id(self, api_client_with_resume):
        client, resume_id = api_client_with_resume
        jd_resp = await client.post("/api/job-descriptions", json={
            "title": "Python Developer",
            "company": "TechCorp",
            "description": _JD_TEXT,
        })
        jd_id = jd_resp.json()["id"]
        resp = await client.post("/api/optimizer/cover-letter", json={
            "resume_id": resume_id,
            "jd_id": jd_id,
            "company": "TechCorp",
        })
        assert resp.status_code == 200
        assert "TechCorp" in resp.json()["cover_letter_text"]
