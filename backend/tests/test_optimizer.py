"""Tests for Features 1, 2, 4, 5: optimizer, diff, interview probability, competitiveness."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.database import Base, get_db
from app.services.resume_optimizer import (
    generate_optimized_resume,
    _reorder_skills,
    _reorder_projects,
    _compute_section_order,
)
from app.services.resume_diff import generate_diff
from app.services.interview_probability import compute_interview_probability
from app.services.competitiveness import analyze_competitiveness

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
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
    yield engine
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Sample data ────────────────────────────────────────────────────────────────

_RESUME_DATA = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "1234567890",
    "linkedin": "linkedin.com/in/alice",
    "github": "github.com/alice",
    "skills": ["python", "django", "postgresql", "docker", "react", "html"],
    "projects": [
        "Built a Django REST API for e-commerce",
        "Created a React dashboard with charts",
        "Worked on a Python data pipeline",
    ],
    "experience_entries": [
        {"start": "Jan 2022", "end": "Dec 2022", "snippet": "Worked on backend services using Python"},
    ],
    "education": [{"degree": "B.Tech Computer Science", "year": "2023"}],
    "certifications": [],
    "sections_detected": ["education", "experience", "projects", "skills"],
    "years_of_experience": 1,
    "raw_text": "Python developer with Django and PostgreSQL experience.",
    "word_count": 300,
}

_JD_TEXT = "We need a Python backend developer with Django, PostgreSQL, and Docker experience. REST API design required."

_JD_INTEL = {
    "critical_requirements": ["python", "django", "postgresql", "docker"],
    "preferred_requirements": ["rest api", "aws"],
    "technologies": {"backend": ["django", "fastapi"], "databases": ["postgresql"], "devops": ["docker"]},
    "qualifications": {
        "experience": {"min_years": 1, "max_years": 3, "is_entry_level": True, "description": "1-3 years"},
        "education": {"level": "bachelor", "description": "Bachelor required"},
        "certifications": [],
    },
    "soft_skills": ["communication"],
}

_GAP = {
    "critical_missing": ["fastapi"],
    "important_missing": ["aws"],
    "optional_missing": [],
    "severity_score": 15,
    "severity_label": "LOW",
    "score_impact": 4,
    "critical_count": 1,
    "important_count": 1,
    "optional_count": 0,
    "summary": "Minor gaps",
}

_PROJ_REL = {
    "has_projects": True,
    "projects": [
        {"index": 0, "score": 85.0, "name": "Django REST API"},
        {"index": 1, "score": 40.0, "name": "React Dashboard"},
        {"index": 2, "score": 30.0, "name": "Python Pipeline"},
    ],
    "average_relevance": 51.7,
    "top_project": "Django REST API",
    "portfolio_summary": "Strong backend projects",
}

_REWRITES: dict = {"skills_section": [], "project_bullets": [], "experience_bullets": [], "priority_list": []}

_ATS = {
    "overall_score": 72.0,
    "keyword_score": 68.0,
    "skills_score": 80.0,
    "experience_score": 60.0,
    "education_score": 75.0,
    "semantic_score": 65.0,
}

_QUALITY = {"quality_score": 78, "quality_label": "GOOD", "issues": [], "high_severity_count": 0}


# ── Tests: section order ───────────────────────────────────────────────────────

class TestSectionOrder:
    def test_fresher_puts_skills_first(self):
        order = _compute_section_order(_RESUME_DATA, _JD_INTEL, _GAP)
        assert order[0] == "skills"

    def test_experienced_puts_experience_first(self):
        exp_resume = {**_RESUME_DATA, "years_of_experience": 5}
        exp_intel = {**_JD_INTEL, "qualifications": {
            "experience": {"is_entry_level": False, "min_years": 5, "max_years": 10, "description": "5+"},
            "education": {"level": "bachelor", "description": ""}, "certifications": [],
        }}
        order = _compute_section_order(exp_resume, exp_intel, _GAP)
        assert order[0] == "experience"

    def test_only_present_sections_returned(self):
        no_certs = {**_RESUME_DATA, "certifications": []}
        order = _compute_section_order(no_certs, _JD_INTEL, _GAP)
        assert "certifications" not in order

    def test_high_critical_gap_prioritises_skills(self):
        big_gap = {**_GAP, "critical_missing": ["a", "b", "c", "d", "e"]}
        exp_resume = {**_RESUME_DATA, "years_of_experience": 5}
        order = _compute_section_order(exp_resume, _JD_INTEL, big_gap)
        assert order[0] == "skills"


# ── Tests: skill reordering ────────────────────────────────────────────────────

class TestSkillReordering:
    def test_jd_matching_skills_go_first(self):
        result = _reorder_skills(["react", "python", "docker"], _JD_INTEL, _JD_TEXT)
        assert "python" in result["primary"] or "docker" in result["primary"]
        assert set(result["all"]) == {"react", "python", "docker"}

    def test_primary_plus_secondary_equals_all(self):
        result = _reorder_skills(_RESUME_DATA["skills"], _JD_INTEL, _JD_TEXT)
        assert set(result["primary"] + result["secondary"]) == set(result["all"])

    def test_empty_skills_returns_empty(self):
        result = _reorder_skills([], _JD_INTEL, _JD_TEXT)
        assert result["all"] == []


# ── Tests: project reordering ──────────────────────────────────────────────────

class TestProjectReordering:
    def test_highest_scored_project_moves_first(self):
        result = _reorder_projects(_RESUME_DATA["projects"], _PROJ_REL)
        assert result[0] == _RESUME_DATA["projects"][0]  # index 0 already has highest score

    def test_reorder_changes_position_when_scores_differ(self):
        projects = ["Low relevance", "High relevance", "Medium relevance"]
        relevance = {
            "projects": [
                {"index": 0, "score": 10.0},
                {"index": 1, "score": 90.0},
                {"index": 2, "score": 50.0},
            ],
            "has_projects": True,
        }
        result = _reorder_projects(projects, relevance)
        assert result[0] == "High relevance"
        assert result[2] == "Low relevance"

    def test_no_relevance_returns_original_order(self):
        result = _reorder_projects(_RESUME_DATA["projects"], {})
        assert result == _RESUME_DATA["projects"]


# ── Tests: generate_optimized_resume ──────────────────────────────────────────

class TestGenerateOptimizedResume:
    def test_returns_required_keys(self):
        opt = generate_optimized_resume(_RESUME_DATA, _JD_TEXT, _JD_INTEL, _GAP, _PROJ_REL, _REWRITES)
        for key in ["name", "contact", "section_order", "skills", "projects", "experience", "education", "changes", "changes_summary"]:
            assert key in opt

    def test_name_preserved(self):
        opt = generate_optimized_resume(_RESUME_DATA, _JD_TEXT, _JD_INTEL, _GAP, _PROJ_REL, _REWRITES)
        assert opt["name"] == "Alice Smith"

    def test_contact_info_preserved(self):
        opt = generate_optimized_resume(_RESUME_DATA, _JD_TEXT, _JD_INTEL, _GAP, _PROJ_REL, _REWRITES)
        assert opt["contact"]["email"] == "alice@example.com"

    def test_skills_split_into_primary_secondary(self):
        opt = generate_optimized_resume(_RESUME_DATA, _JD_TEXT, _JD_INTEL, _GAP, _PROJ_REL, _REWRITES)
        assert isinstance(opt["skills"]["primary"], list)
        assert isinstance(opt["skills"]["secondary"], list)

    def test_project_entries_have_required_keys(self):
        opt = generate_optimized_resume(_RESUME_DATA, _JD_TEXT, _JD_INTEL, _GAP, _PROJ_REL, _REWRITES)
        for p in opt["projects"]:
            assert "original" in p
            assert "optimized" in p
            assert "safety" in p

    def test_safety_flags_are_valid(self):
        opt = generate_optimized_resume(_RESUME_DATA, _JD_TEXT, _JD_INTEL, _GAP, _PROJ_REL, _REWRITES)
        for p in opt["projects"]:
            assert p["safety"] in ("SAFE", "REQUIRES_VERIFICATION")

    def test_empty_resume_does_not_crash(self):
        opt = generate_optimized_resume({}, _JD_TEXT, _JD_INTEL, _GAP, {}, _REWRITES)
        assert "section_order" in opt


# ── Tests: resume diff ────────────────────────────────────────────────────────

class TestResumeDiff:
    def _make_optimized(self, extra_changes=None):
        changes = [
            {"type": "REORDERED", "section": "sections", "description": "Reordered", "original": [], "optimized": []},
            {"type": "REWRITTEN", "section": "projects", "description": "Improved", "original": "old", "optimized": "new", "safety": "SAFE"},
        ]
        if extra_changes:
            changes.extend(extra_changes)
        return {"changes": changes}

    def test_diff_categories_present(self):
        diff = generate_diff(_RESUME_DATA, self._make_optimized())
        for key in ["added", "removed", "reordered", "rewritten", "total_changes", "has_changes", "summary"]:
            assert key in diff

    def test_reordered_count(self):
        diff = generate_diff(_RESUME_DATA, self._make_optimized())
        assert len(diff["reordered"]) == 1

    def test_rewritten_count(self):
        diff = generate_diff(_RESUME_DATA, self._make_optimized())
        assert len(diff["rewritten"]) == 1

    def test_total_changes(self):
        diff = generate_diff(_RESUME_DATA, self._make_optimized())
        assert diff["total_changes"] == 2

    def test_summary_not_empty_when_changes(self):
        diff = generate_diff(_RESUME_DATA, self._make_optimized())
        assert diff["summary"] != "No changes"

    def test_no_changes_returns_empty(self):
        diff = generate_diff(_RESUME_DATA, {"changes": []})
        assert diff["total_changes"] == 0
        assert not diff["has_changes"]
        assert diff["summary"] == "No changes"


# ── Tests: interview probability ───────────────────────────────────────────────

class TestInterviewProbability:
    def test_returns_required_keys(self):
        result = compute_interview_probability(_ATS, _GAP, _PROJ_REL, _QUALITY)
        for key in ["probability", "label", "factors", "reasoning", "top_strength", "main_bottleneck"]:
            assert key in result

    def test_probability_in_range(self):
        result = compute_interview_probability(_ATS, _GAP, _PROJ_REL, _QUALITY)
        assert 0 <= result["probability"] <= 100

    def test_label_is_valid(self):
        result = compute_interview_probability(_ATS, _GAP, _PROJ_REL, _QUALITY)
        assert result["label"] in ("HIGH", "MEDIUM", "LOW", "VERY LOW")

    def test_six_factors(self):
        result = compute_interview_probability(_ATS, _GAP, _PROJ_REL, _QUALITY)
        assert len(result["factors"]) == 6

    def test_high_gap_severity_reduces_probability(self):
        bad_gap = {**_GAP, "severity_score": 90}
        good = compute_interview_probability(_ATS, _GAP, _PROJ_REL, _QUALITY)
        bad = compute_interview_probability(_ATS, bad_gap, _PROJ_REL, _QUALITY)
        assert bad["probability"] < good["probability"]

    def test_no_project_relevance_uses_fallback(self):
        result = compute_interview_probability(_ATS, _GAP, None, _QUALITY)
        assert 0 <= result["probability"] <= 100

    def test_high_scores_give_high_label(self):
        great_ats = {"overall_score": 95, "skills_score": 95, "education_score": 95, "semantic_score": 90}
        great_gap = {**_GAP, "severity_score": 5}
        great_qual = {**_QUALITY, "quality_score": 95}
        result = compute_interview_probability(great_ats, great_gap, _PROJ_REL, great_qual)
        assert result["label"] in ("HIGH", "MEDIUM")

    def test_low_scores_give_low_label(self):
        bad_ats = {"overall_score": 10, "skills_score": 10, "education_score": 10, "semantic_score": 10}
        bad_gap = {**_GAP, "severity_score": 95}
        bad_qual = {**_QUALITY, "quality_score": 20}
        result = compute_interview_probability(bad_ats, bad_gap, None, bad_qual)
        assert result["label"] in ("LOW", "VERY LOW")


# ── Tests: competitiveness ────────────────────────────────────────────────────

class TestCompetitiveness:
    def test_returns_required_keys(self):
        result = analyze_competitiveness(_ATS, _GAP, _PROJ_REL)
        for key in ["label", "label_key", "composite_score", "explanation", "detailed_factors"]:
            assert key in result

    def test_label_key_is_valid(self):
        result = analyze_competitiveness(_ATS, _GAP, _PROJ_REL)
        assert result["label_key"] in ("STRONG_MATCH", "REASONABLE_MATCH", "STRETCH", "LOW_PROBABILITY")

    def test_composite_in_range(self):
        result = analyze_competitiveness(_ATS, _GAP, _PROJ_REL)
        assert 0 <= result["composite_score"] <= 100

    def test_high_score_gives_strong_match(self):
        great_ats = {**_ATS, "overall_score": 90}
        no_gap = {**_GAP, "severity_score": 5, "critical_count": 0}
        result = analyze_competitiveness(great_ats, no_gap, _PROJ_REL)
        assert result["label_key"] == "STRONG_MATCH"

    def test_low_score_gives_low_probability(self):
        bad_ats = {**_ATS, "overall_score": 20}
        bad_gap = {**_GAP, "severity_score": 90, "critical_count": 8}
        result = analyze_competitiveness(bad_ats, bad_gap, None)
        assert result["label_key"] == "LOW_PROBABILITY"

    def test_no_project_relevance_still_works(self):
        result = analyze_competitiveness(_ATS, _GAP, None)
        assert "label" in result

    def test_explanation_contains_ats_score(self):
        result = analyze_competitiveness(_ATS, _GAP, _PROJ_REL)
        assert "72" in result["explanation"]


# ── API integration tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_optimizer_generate_no_resume(client):
    payload = {"resume_id": 9999, "jd_text": "Python developer required"}
    response = await client.post("/api/optimizer/generate", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_docx(client):
    optimized = {
        "name": "Test User",
        "contact": {"email": "test@test.com", "phone": "1234"},
        "section_order": ["skills", "projects"],
        "skills": {"primary": ["python"], "secondary": ["js"], "all": ["python", "js"]},
        "projects": [{"original": "Built X", "optimized": "Developed X", "safety": "SAFE"}],
        "experience": [],
        "education": [{"degree": "B.Tech", "year": "2023"}],
        "certifications": [],
    }
    response = await client.post("/api/optimizer/export/docx", json=optimized)
    assert response.status_code == 200
    assert "application/vnd" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_export_pdf(client):
    optimized = {
        "name": "Test User",
        "contact": {"email": "test@test.com"},
        "section_order": ["skills"],
        "skills": {"primary": ["python"], "secondary": [], "all": ["python"]},
        "projects": [],
        "experience": [],
        "education": [],
        "certifications": [],
    }
    response = await client.post("/api/optimizer/export/pdf", json=optimized)
    assert response.status_code == 200
    assert "pdf" in response.headers["content-type"]
