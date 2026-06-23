"""Tests for Feature 6: Market Analyzer."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.database import Base, get_db
from app.services.market_analyzer import analyze_market

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


_JDS = [
    "Python developer with Django and PostgreSQL required. Docker and AWS experience a plus.",
    "Python and FastAPI backend developer. PostgreSQL, Docker required. CI/CD experience needed.",
    "Full stack developer: Python, React, PostgreSQL, Docker. AWS knowledge preferred.",
    "Python engineer with Django, REST APIs, Docker, and Kubernetes experience.",
    "Senior Python developer. Django, PostgreSQL, Redis, Docker, AWS required.",
]


class TestMarketAnalyzerService:
    def test_empty_jds_returns_empty(self):
        result = analyze_market([])
        assert result["jd_count"] == 0
        assert result["top_skills"] == []

    def test_jd_count_correct(self):
        result = analyze_market(_JDS)
        assert result["jd_count"] == len(_JDS)

    def test_top_skills_not_empty(self):
        result = analyze_market(_JDS)
        assert len(result["top_skills"]) > 0

    def test_python_is_top_skill(self):
        result = analyze_market(_JDS)
        top_names = [s["skill"] for s in result["top_skills"]]
        assert "python" in top_names

    def test_returns_all_required_keys(self):
        result = analyze_market(_JDS)
        for key in ["jd_count", "total_unique_skills", "top_skills", "top_languages",
                    "top_frameworks", "top_tools", "top_cloud", "top_databases",
                    "top_concepts", "missing_from_profile", "profile_provided"]:
            assert key in result

    def test_missing_from_profile_empty_when_no_resume(self):
        result = analyze_market(_JDS)
        assert result["missing_from_profile"] == []
        assert result["profile_provided"] is False

    def test_missing_from_profile_computed_when_resume_given(self):
        resume_skills = ["python"]  # missing docker, postgresql, etc.
        result = analyze_market(_JDS, resume_skills)
        assert result["profile_provided"] is True
        missing_names = [s["skill"] for s in result["missing_from_profile"]]
        assert "docker" in missing_names or "postgresql" in missing_names

    def test_percentage_in_range(self):
        result = analyze_market(_JDS)
        for entry in result["top_skills"]:
            assert 0 <= entry["percentage"] <= 100

    def test_count_never_exceeds_jd_count(self):
        result = analyze_market(_JDS)
        n = result["jd_count"]
        for entry in result["top_skills"]:
            assert entry["count"] <= n

    def test_single_jd(self):
        result = analyze_market(["Python developer with Django"])
        assert result["jd_count"] == 1
        assert len(result["top_skills"]) > 0

    def test_profile_provided_false_when_none(self):
        result = analyze_market(_JDS, None)
        assert result["profile_provided"] is False

    def test_profile_provided_true_even_if_empty_list(self):
        result = analyze_market(_JDS, [])
        assert result["profile_provided"] is True


class TestMarketApiEndpoint:
    @pytest.mark.asyncio
    async def test_analyze_with_jd_texts(self, client):
        payload = {"jd_texts": _JDS[:3]}
        response = await client.post("/api/market/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["jd_count"] == 3

    @pytest.mark.asyncio
    async def test_analyze_empty_request_returns_400(self, client):
        response = await client.post("/api/market/analyze", json={})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_analyze_with_nonexistent_resume(self, client):
        response = await client.post("/api/market/analyze", json={
            "jd_texts": ["Python developer"],
            "resume_id": 9999,
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_analyze_returns_top_skills(self, client):
        response = await client.post("/api/market/analyze", json={"jd_texts": _JDS})
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_skills"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_with_saved_jd(self, client):
        # Create a JD first
        create_resp = await client.post("/api/job-descriptions", json={
            "title": "Python Dev",
            "company": "Acme",
            "description": "Python developer with Django and Docker",
        })
        jd_id = create_resp.json()["id"]
        response = await client.post("/api/market/analyze", json={"jd_ids": [jd_id]})
        assert response.status_code == 200
        data = response.json()
        assert data["jd_count"] == 1
