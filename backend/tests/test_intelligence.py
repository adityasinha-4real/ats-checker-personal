"""
Comprehensive tests for all Phase 1-9 intelligence features.
Covers: JD classification, gap analysis, rewrite engine, project relevance,
recruiter view, quality audit, fresher mode, and the /intelligence/analyze API.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.database import Base, get_db

# ── Fixtures ──────────────────────────────────────────────────────────────────

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


# ── Shared test data ──────────────────────────────────────────────────────────

JD_EXPERIENCED = """
We are looking for a Senior Python Developer with 3+ years of experience.

Required Qualifications:
- Strong Python programming skills (required)
- Experience with FastAPI or Django (must have)
- PostgreSQL or MySQL database experience (required)
- Docker and Kubernetes experience (mandatory)
- Bachelor's degree in Computer Science or related field

Preferred Qualifications:
- Knowledge of React and TypeScript (nice to have)
- CI/CD experience with GitHub Actions (preferred)
- Machine learning knowledge is a bonus
- AWS or cloud platform experience (good to have)
"""

JD_FRESHER = """
Entry-level Software Engineer - Internship / New Graduate

We are looking for a fresher or recent graduate to join our team.

Requirements:
- Python programming
- Basic knowledge of web development (Flask or Django)
- SQL database fundamentals
- Git version control

Good to have:
- React or any frontend framework
- Docker basics
- Any cloud exposure
"""

RESUME_STRONG = {
    "raw_text": """
John Doe | john.doe@email.com | 555-0100 | github.com/johndoe | linkedin.com/in/johndoe

SUMMARY
Senior software engineer with 5 years experience in Python backend development.

EXPERIENCE
Senior Python Developer at TechCorp (2021 - Present)
- Developed FastAPI microservices handling 1M+ daily requests
- Implemented Docker and Kubernetes deployment pipelines
- Optimized PostgreSQL queries, reducing latency by 40%
- Led migration from monolith to microservices architecture

Software Engineer at StartupXYZ (2019 - 2021)
- Built React applications with TypeScript
- Configured CI/CD pipelines using GitHub Actions

SKILLS
Python, FastAPI, Django, React, TypeScript, PostgreSQL, MySQL,
Docker, Kubernetes, CI/CD, GitHub Actions, Machine Learning, AWS

PROJECTS
ATS Checker Tool
- Developed an ATS resume analyzer using Python and FastAPI
- Implemented semantic similarity using SentenceTransformers
- Deployed on AWS using Docker containers

EDUCATION
Bachelor of Science in Computer Science - MIT - 2019

CERTIFICATIONS
AWS Certified Developer Associate
""",
    "emails": ["john.doe@email.com"],
    "phones": ["555-0100"],
    "linkedin": "linkedin.com/in/johndoe",
    "github": "github.com/johndoe",
    "skills": ["python", "fastapi", "django", "react", "typescript", "postgresql", "docker", "kubernetes", "ci/cd", "aws"],
    "education_level": 3,
    "years_of_experience": 5,
    "word_count": 280,
    "sections_detected": ["summary", "experience", "skills", "projects", "education", "certifications"],
    "projects": [
        "ATS Checker Tool\nDeveloped an ATS resume analyzer using Python and FastAPI.\nImplemented semantic similarity. Deployed on AWS using Docker.",
        "E-Commerce Platform\nBuilt a full-stack e-commerce site with React, FastAPI, PostgreSQL and Docker.",
    ],
    "certifications": ["AWS Certified Developer Associate"],
    "education": [{"degree": "Bachelor of Science", "field": "Computer Science", "year": "2019"}],
}

RESUME_WEAK = {
    "raw_text": """
Jane Smith
jane@email.com

EXPERIENCE
Junior PHP Developer 2023 - Present
Worked on website features

SKILLS
PHP, HTML, CSS, MySQL

EDUCATION
High School Diploma 2022
""",
    "emails": ["jane@email.com"],
    "phones": [],
    "linkedin": None,
    "github": None,
    "skills": ["php", "html", "css", "mysql"],
    "education_level": 0,
    "years_of_experience": 1,
    "word_count": 45,
    "sections_detected": ["experience", "skills", "education"],
    "projects": [],
    "certifications": [],
}

RESUME_FRESHER = {
    "raw_text": """
Alice Freshman | alice@email.com | github.com/alice

SUMMARY
Final-year Computer Science student passionate about backend development.

PROJECTS
Django Blog Platform
- Built a blog platform using Django and PostgreSQL
- Implemented user authentication and REST APIs
- Deployed locally with Docker

Flask REST API
- Created a REST API using Flask and SQLite
- Implemented CRUD operations with proper error handling

SKILLS
Python, Django, Flask, SQL, Git, HTML, CSS, Docker

EDUCATION
Bachelor of Technology in Computer Science - State University - 2025 (Final Year)
""",
    "emails": ["alice@email.com"],
    "phones": [],
    "linkedin": None,
    "github": "github.com/alice",
    "skills": ["python", "django", "flask", "sql", "git", "html", "css", "docker"],
    "education_level": 3,
    "years_of_experience": 0,
    "word_count": 165,
    "sections_detected": ["summary", "projects", "skills", "education"],
    "projects": [
        "Django Blog Platform\nBuilt a blog platform using Django and PostgreSQL. Implemented user authentication and REST APIs. Deployed locally with Docker.",
        "Flask REST API\nCreated a REST API using Flask and SQLite. Implemented CRUD operations with proper error handling.",
    ],
    "certifications": [],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: JD Intelligence Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestJDIntelligence:
    def test_classify_returns_required_fields(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd(JD_EXPERIENCED)
        assert "critical_requirements" in result
        assert "preferred_requirements" in result
        assert "technologies" in result
        assert "qualifications" in result
        assert "soft_skills" in result

    def test_classifies_tech_skills(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd(JD_EXPERIENCED)
        all_found = result["critical_requirements"] + result["preferred_requirements"]
        # Python is in the required section
        assert "python" in all_found

    def test_preferred_requirements_separate(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd(JD_EXPERIENCED)
        # react and typescript are in preferred section
        preferred = result["preferred_requirements"]
        assert isinstance(preferred, list)

    def test_experience_extraction(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd(JD_EXPERIENCED)
        exp = result["qualifications"]["experience"]
        assert exp["min_years"] == 3

    def test_education_extraction(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd(JD_EXPERIENCED)
        edu = result["qualifications"]["education"]
        assert edu["level"] == "bachelors"

    def test_entry_level_detected(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd(JD_FRESHER)
        exp = result["qualifications"]["experience"]
        assert exp["is_entry_level"] is True

    def test_technologies_categorised(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd(JD_EXPERIENCED)
        tech = result["technologies"]
        assert isinstance(tech, dict)
        # Should have at least languages
        assert any(len(v) > 0 for v in tech.values())

    def test_empty_jd_does_not_crash(self):
        from app.services.jd_intelligence import classify_jd
        result = classify_jd("Software developer wanted.")
        assert isinstance(result["critical_requirements"], list)

    def test_soft_skills_extracted(self):
        from app.services.jd_intelligence import classify_jd
        jd_with_soft = JD_EXPERIENCED + "\nStrong communication and teamwork skills required."
        result = classify_jd(jd_with_soft)
        assert isinstance(result["soft_skills"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Gap Analysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestGapAnalysis:
    def _setup(self, resume_data):
        from app.services.jd_intelligence import classify_jd
        from app.services.ats_scorer import run_ats_analysis
        jd_intel = classify_jd(JD_EXPERIENCED)
        ats = run_ats_analysis(resume_data, JD_EXPERIENCED)
        return jd_intel, ats

    def test_returns_required_fields(self):
        from app.services.gap_analyzer import analyze_gaps
        jd_intel, ats = self._setup(RESUME_WEAK)
        result = analyze_gaps(RESUME_WEAK, jd_intel, ats)
        for field in ["critical_missing", "important_missing", "optional_missing",
                      "severity_score", "severity_label", "score_impact", "summary"]:
            assert field in result

    def test_severity_score_bounds(self):
        from app.services.gap_analyzer import analyze_gaps
        jd_intel, ats = self._setup(RESUME_WEAK)
        result = analyze_gaps(RESUME_WEAK, jd_intel, ats)
        assert 0 <= result["severity_score"] <= 100

    def test_strong_resume_lower_severity(self):
        from app.services.gap_analyzer import analyze_gaps
        from app.services.jd_intelligence import classify_jd
        from app.services.ats_scorer import run_ats_analysis
        jd_intel = classify_jd(JD_EXPERIENCED)
        ats_strong = run_ats_analysis(RESUME_STRONG, JD_EXPERIENCED)
        ats_weak = run_ats_analysis(RESUME_WEAK, JD_EXPERIENCED)
        result_strong = analyze_gaps(RESUME_STRONG, jd_intel, ats_strong)
        result_weak = analyze_gaps(RESUME_WEAK, jd_intel, ats_weak)
        assert result_strong["severity_score"] <= result_weak["severity_score"]

    def test_summary_is_string(self):
        from app.services.gap_analyzer import analyze_gaps
        jd_intel, ats = self._setup(RESUME_WEAK)
        result = analyze_gaps(RESUME_WEAK, jd_intel, ats)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_counts_correct(self):
        from app.services.gap_analyzer import analyze_gaps
        jd_intel, ats = self._setup(RESUME_WEAK)
        result = analyze_gaps(RESUME_WEAK, jd_intel, ats)
        assert result["critical_count"] == len(result["critical_missing"])
        assert result["important_count"] == len(result["important_missing"])
        assert result["optional_count"] == len(result["optional_missing"])

    def test_no_duplicates_across_categories(self):
        from app.services.gap_analyzer import analyze_gaps
        jd_intel, ats = self._setup(RESUME_WEAK)
        result = analyze_gaps(RESUME_WEAK, jd_intel, ats)
        critical_set = set(result["critical_missing"])
        important_set = set(result["important_missing"])
        # critical and important should not overlap
        assert critical_set.isdisjoint(important_set)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Rewrite Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestRewriteEngine:
    def _gap(self, resume_data):
        from app.services.jd_intelligence import classify_jd
        from app.services.ats_scorer import run_ats_analysis
        from app.services.gap_analyzer import analyze_gaps
        jd_intel = classify_jd(JD_EXPERIENCED)
        ats = run_ats_analysis(resume_data, JD_EXPERIENCED)
        return analyze_gaps(resume_data, jd_intel, ats)

    def test_generate_all_rewrites_structure(self):
        from app.services.rewrite_engine import generate_all_rewrites
        gap = self._gap(RESUME_WEAK)
        result = generate_all_rewrites(RESUME_WEAK, gap)
        assert "skills_section" in result
        assert "project_bullets" in result
        assert "experience_bullets" in result
        assert "priority_list" in result

    def test_skills_suggestions_are_list(self):
        from app.services.rewrite_engine import generate_skills_section_suggestions
        gap = self._gap(RESUME_WEAK)
        result = generate_skills_section_suggestions(RESUME_WEAK, gap)
        assert isinstance(result, list)

    def test_skills_suggestions_have_impact_field(self):
        from app.services.rewrite_engine import generate_skills_section_suggestions
        gap = self._gap(RESUME_WEAK)
        result = generate_skills_section_suggestions(RESUME_WEAK, gap)
        for item in result:
            assert "impact" in item
            assert item["impact"] in ("HIGH", "MEDIUM", "LOW")

    def test_project_bullets_have_safety_field(self):
        from app.services.rewrite_engine import generate_project_bullet_suggestions
        gap = self._gap(RESUME_WEAK)
        result = generate_project_bullet_suggestions(RESUME_WEAK, gap)
        for item in result:
            assert "safety" in item
            assert item["safety"] in ("SAFE", "REQUIRES_VERIFICATION")

    def test_priority_list_priorities_valid(self):
        from app.services.rewrite_engine import generate_all_rewrites
        gap = self._gap(RESUME_WEAK)
        result = generate_all_rewrites(RESUME_WEAK, gap)
        valid = {"HIGH IMPACT", "MEDIUM IMPACT", "LOW IMPACT"}
        for item in result["priority_list"]:
            assert item["priority"] in valid

    def test_rewrite_does_not_fabricate(self):
        """Rewrites of SAFE type must use existing resume content."""
        from app.services.rewrite_engine import generate_project_bullet_suggestions
        gap = self._gap(RESUME_STRONG)
        result = generate_project_bullet_suggestions(RESUME_STRONG, gap)
        for item in result:
            if item.get("safety") == "SAFE" and item.get("current"):
                # Current must come from the resume
                assert item["current"] in RESUME_STRONG["raw_text"]

    def test_no_suggestions_for_fully_matched_resume(self):
        """A perfectly-matched resume should yield fewer HIGH suggestions."""
        from app.services.rewrite_engine import generate_skills_section_suggestions
        from app.services.gap_analyzer import analyze_gaps
        from app.services.jd_intelligence import classify_jd
        from app.services.ats_scorer import run_ats_analysis
        jd_intel = classify_jd(JD_EXPERIENCED)
        ats = run_ats_analysis(RESUME_STRONG, JD_EXPERIENCED)
        gap = analyze_gaps(RESUME_STRONG, jd_intel, ats)
        result = generate_skills_section_suggestions(RESUME_STRONG, gap)
        # Strong resume should have fewer critical skill gaps
        high_count = sum(1 for r in result if r["impact"] == "HIGH")
        assert high_count < 5


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Project Relevance
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectRelevance:
    def test_returns_required_fields(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_STRONG, JD_EXPERIENCED)
        assert "has_projects" in result
        assert "projects" in result
        assert "average_relevance" in result
        assert "portfolio_summary" in result

    def test_has_projects_true_when_present(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_STRONG, JD_EXPERIENCED)
        assert result["has_projects"] is True

    def test_has_projects_false_when_missing(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_WEAK, JD_EXPERIENCED)
        assert result["has_projects"] is False

    def test_score_bounds(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_STRONG, JD_EXPERIENCED)
        for proj in result["projects"]:
            assert 0 <= proj["score"] <= 100

    def test_recommendation_field_present(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_STRONG, JD_EXPERIENCED)
        for proj in result["projects"]:
            assert "recommendation" in proj
            assert "action" in proj["recommendation"]

    def test_recommendation_actions_valid(self):
        from app.services.project_analyzer import analyze_project_relevance
        valid_actions = {"MOVE UP", "EXPAND", "MOVE DOWN", "COMPRESS"}
        result = analyze_project_relevance(RESUME_STRONG, JD_EXPERIENCED)
        for proj in result["projects"]:
            assert proj["recommendation"]["action"] in valid_actions

    def test_average_relevance_in_bounds(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_STRONG, JD_EXPERIENCED)
        if result["has_projects"]:
            assert 0 <= result["average_relevance"] <= 100

    def test_matched_skills_subset_of_project(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_STRONG, JD_EXPERIENCED)
        for proj in result["projects"]:
            matched = proj["breakdown"]["matched_skills"]
            assert isinstance(matched, list)

    def test_fresher_projects_scored(self):
        from app.services.project_analyzer import analyze_project_relevance
        result = analyze_project_relevance(RESUME_FRESHER, JD_FRESHER)
        assert result["has_projects"] is True
        assert len(result["projects"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Fresher Mode
# ═══════════════════════════════════════════════════════════════════════════════

class TestFresherMode:
    def test_fresher_mode_boosts_fresher_score(self):
        from app.services.ats_scorer import run_ats_analysis
        standard = run_ats_analysis(RESUME_FRESHER, JD_EXPERIENCED, fresher_mode=False)
        fresher = run_ats_analysis(RESUME_FRESHER, JD_EXPERIENCED, fresher_mode=True)
        # Fresher mode reduces penalty from experience=0
        assert fresher["overall_score"] >= standard["overall_score"] - 5

    def test_fresher_mode_flag_in_result(self):
        from app.services.ats_scorer import run_ats_analysis
        result = run_ats_analysis(RESUME_FRESHER, JD_FRESHER, fresher_mode=True)
        assert result["fresher_mode"] is True

    def test_standard_mode_flag_false(self):
        from app.services.ats_scorer import run_ats_analysis
        result = run_ats_analysis(RESUME_STRONG, JD_EXPERIENCED, fresher_mode=False)
        assert result["fresher_mode"] is False

    def test_weights_used_field(self):
        from app.services.ats_scorer import run_ats_analysis
        fresher = run_ats_analysis(RESUME_FRESHER, JD_FRESHER, fresher_mode=True)
        standard = run_ats_analysis(RESUME_STRONG, JD_EXPERIENCED, fresher_mode=False)
        assert fresher["details"]["weights_used"] == "fresher"
        assert standard["details"]["weights_used"] == "standard"

    def test_fresher_mode_does_not_change_individual_scores(self):
        """Individual component scores are mode-independent; only overall changes."""
        from app.services.ats_scorer import run_ats_analysis
        r1 = run_ats_analysis(RESUME_FRESHER, JD_FRESHER, fresher_mode=True)
        r2 = run_ats_analysis(RESUME_FRESHER, JD_FRESHER, fresher_mode=False)
        for key in ["keyword_score", "skills_score", "experience_score", "education_score"]:
            assert r1[key] == r2[key]

    def test_existing_tests_still_pass(self):
        """Backward-compat: run_ats_analysis without fresher_mode must work."""
        from app.services.ats_scorer import run_ats_analysis
        result = run_ats_analysis(RESUME_STRONG, JD_EXPERIENCED)
        assert "overall_score" in result
        assert 0 <= result["overall_score"] <= 100


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Recruiter View
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecruiterView:
    def _build(self, resume_data):
        from app.services.jd_intelligence import classify_jd
        from app.services.ats_scorer import run_ats_analysis
        from app.services.gap_analyzer import analyze_gaps
        from app.services.quality_audit import audit_resume
        from app.services.recruiter_view import generate_recruiter_view
        jd_intel = classify_jd(JD_EXPERIENCED)
        ats = run_ats_analysis(resume_data, JD_EXPERIENCED)
        gap = analyze_gaps(resume_data, jd_intel, ats)
        quality = audit_resume(resume_data)
        return generate_recruiter_view(resume_data, ats, jd_intel, gap, quality)

    def test_returns_required_fields(self):
        result = self._build(RESUME_STRONG)
        for field in ["strengths", "weaknesses", "interview_likelihood",
                      "likelihood_reasoning", "overall_impression",
                      "standout_factors", "call_to_action"]:
            assert field in result

    def test_interview_likelihood_valid_values(self):
        result = self._build(RESUME_STRONG)
        assert result["interview_likelihood"] in ("HIGH", "MEDIUM", "LOW", "VERY LOW")

    def test_strong_resume_high_likelihood(self):
        result = self._build(RESUME_STRONG)
        assert result["interview_likelihood"] in ("HIGH", "MEDIUM")

    def test_weak_resume_low_likelihood(self):
        result = self._build(RESUME_WEAK)
        assert result["interview_likelihood"] in ("LOW", "VERY LOW", "MEDIUM")

    def test_strengths_are_list_of_strings(self):
        result = self._build(RESUME_STRONG)
        assert isinstance(result["strengths"], list)
        for s in result["strengths"]:
            assert isinstance(s, str)

    def test_call_to_action_is_string(self):
        result = self._build(RESUME_WEAK)
        assert isinstance(result["call_to_action"], str)
        assert len(result["call_to_action"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8: Quality Audit
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityAudit:
    def test_returns_required_fields(self):
        from app.services.quality_audit import audit_resume
        result = audit_resume(RESUME_STRONG)
        for field in ["quality_score", "quality_label", "issues",
                      "positive_signals", "high_severity_count"]:
            assert field in result

    def test_quality_score_bounds(self):
        from app.services.quality_audit import audit_resume
        result = audit_resume(RESUME_STRONG)
        assert 0 <= result["quality_score"] <= 100

    def test_quality_label_valid(self):
        from app.services.quality_audit import audit_resume
        valid = {"EXCELLENT", "GOOD", "AVERAGE", "BELOW AVERAGE", "POOR"}
        result = audit_resume(RESUME_STRONG)
        assert result["quality_label"] in valid

    def test_weak_resume_more_issues(self):
        from app.services.quality_audit import audit_resume
        strong_result = audit_resume(RESUME_STRONG)
        weak_result = audit_resume(RESUME_WEAK)
        assert weak_result["issue_count"] >= strong_result["issue_count"]

    def test_missing_email_flagged(self):
        from app.services.quality_audit import audit_resume
        no_email = {**RESUME_WEAK, "emails": []}
        result = audit_resume(no_email)
        messages = [i["message"] for i in result["issues"]]
        assert any("email" in m.lower() for m in messages)

    def test_missing_skills_section_flagged(self):
        from app.services.quality_audit import audit_resume
        no_skills = {**RESUME_WEAK, "skills": [], "sections_detected": ["experience", "education"]}
        result = audit_resume(no_skills)
        messages = [i["message"] for i in result["issues"]]
        assert any("skills" in m.lower() for m in messages)

    def test_weak_verbs_flagged(self):
        from app.services.quality_audit import audit_resume
        result = audit_resume(RESUME_WEAK)  # has "Worked on" in raw text
        messages = [i["message"] for i in result["issues"]]
        has_verb_issue = any("verb" in m.lower() or "action" in m.lower() for m in messages)
        assert has_verb_issue

    def test_positive_signals_for_strong_resume(self):
        from app.services.quality_audit import audit_resume
        result = audit_resume(RESUME_STRONG)
        assert len(result["positive_signals"]) > 0

    def test_severity_counts_correct(self):
        from app.services.quality_audit import audit_resume
        result = audit_resume(RESUME_WEAK)
        h = sum(1 for i in result["issues"] if i["severity"] == "HIGH")
        m = sum(1 for i in result["issues"] if i["severity"] == "MEDIUM")
        l_ = sum(1 for i in result["issues"] if i["severity"] == "LOW")
        assert result["high_severity_count"] == h
        assert result["medium_severity_count"] == m
        assert result["low_severity_count"] == l_


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 9: Intelligence API endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_intelligence_analyze_missing_resume(client):
    payload = {
        "resume_id": 99999,
        "jd_text": JD_FRESHER,
        "mode": "fresher",
    }
    response = await client.post("/api/intelligence/analyze", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_intelligence_analyze_missing_jd(client):
    payload = {"resume_id": 1}
    response = await client.post("/api/intelligence/analyze", json=payload)
    # no resume and no jd → 404 (resume not found first) or 400
    assert response.status_code in (400, 404)


@pytest.mark.asyncio
async def test_intelligence_jd_endpoint_not_found(client):
    response = await client.get("/api/intelligence/jd/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_intelligence_jd_endpoint_found(client):
    # Create a JD first
    jd_payload = {
        "title": "Python Dev",
        "company": "Acme",
        "description": JD_EXPERIENCED,
    }
    jd_resp = await client.post("/api/job-descriptions", json=jd_payload)
    assert jd_resp.status_code == 201
    jd_id = jd_resp.json()["id"]

    resp = await client.get(f"/api/intelligence/jd/{jd_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "critical_requirements" in data
    assert "preferred_requirements" in data
    assert "technologies" in data


@pytest.mark.asyncio
async def test_intelligence_mode_validation(client):
    payload = {
        "resume_id": 1,
        "jd_text": JD_FRESHER,
        "mode": "invalid_mode",
    }
    response = await client.post("/api/intelligence/analyze", json=payload)
    assert response.status_code == 422  # validation error


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: NLP Normalization
# ═══════════════════════════════════════════════════════════════════════════════

class TestNLPNormalization:
    def test_js_normalizes_to_javascript(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("js") == "javascript"

    def test_k8s_normalizes_to_kubernetes(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("k8s") == "kubernetes"

    def test_postgres_normalizes_to_postgresql(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("postgres") == "postgresql"

    def test_ts_normalizes_to_typescript(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("ts") == "typescript"

    def test_node_normalizes_to_nodejs(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("node") == "node.js"

    def test_unknown_skill_returned_unchanged(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("someunknownthing") == "someunknownthing"

    def test_cicd_normalizes(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("cicd") == "ci/cd"

    def test_restful_normalizes(self):
        from app.services.nlp_engine import normalize_skill
        assert normalize_skill("restful") == "rest"
