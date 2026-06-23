"""Tests for Skill Gap Roadmap (Feature 4 of v4.0)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.database import Base, get_db
from app.services.skill_roadmap import generate_roadmap

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_MISSING_SKILLS = [
    {"skill": "Kubernetes", "count": 8, "percentage": 80, "category": "cloud"},
    {"skill": "TypeScript", "count": 7, "percentage": 70, "category": "programming_languages"},
    {"skill": "GraphQL", "count": 5, "percentage": 50, "category": "frameworks"},
    {"skill": "Redis", "count": 4, "percentage": 40, "category": "databases"},
    {"skill": "Terraform", "count": 3, "percentage": 30, "category": "tools"},
    {"skill": "Go", "count": 3, "percentage": 30, "category": "programming_languages"},
    {"skill": "Kafka", "count": 2, "percentage": 20, "category": "tools"},
]


class TestSkillRoadmapService:
    def test_returns_required_keys(self):
        result = generate_roadmap(_MISSING_SKILLS)
        assert "phases" in result
        assert "total_skills" in result
        assert "total_phases" in result
        assert "learning_focus" in result

    def test_total_skills_count(self):
        result = generate_roadmap(_MISSING_SKILLS)
        assert result["total_skills"] == len(_MISSING_SKILLS)

    def test_phases_structure(self):
        result = generate_roadmap(_MISSING_SKILLS)
        for phase in result["phases"]:
            assert "phase" in phase
            assert "label" in phase
            assert "timeframe" in phase
            assert "skills" in phase

    def test_skills_sorted_by_priority(self):
        result = generate_roadmap(_MISSING_SKILLS)
        # Phase 1 should contain the highest-priority skill
        phase1_skills = result["phases"][0]["skills"]
        # TypeScript (lang, score=70*1.5=105) and Kubernetes (cloud, 80*1.2=96) should be top
        phase1_names = {s["skill"] for s in phase1_skills}
        assert "TypeScript" in phase1_names  # highest priority score

    def test_phase1_is_immediate(self):
        result = generate_roadmap(_MISSING_SKILLS)
        assert result["phases"][0]["label"] == "Immediate Priority"
        assert "0–3" in result["phases"][0]["timeframe"]

    def test_phase1_has_max_5_skills(self):
        result = generate_roadmap(_MISSING_SKILLS)
        assert len(result["phases"][0]["skills"]) <= 5

    def test_each_skill_has_why(self):
        result = generate_roadmap(_MISSING_SKILLS)
        for phase in result["phases"]:
            for skill in phase["skills"]:
                assert skill["why"]
                assert len(skill["why"]) > 5

    def test_each_skill_has_market_demand(self):
        result = generate_roadmap(_MISSING_SKILLS)
        for phase in result["phases"]:
            for skill in phase["skills"]:
                assert 0 <= skill["market_demand"] <= 100

    def test_empty_missing_skills(self):
        result = generate_roadmap([])
        assert result["total_skills"] == 0
        assert result["total_phases"] == 0
        assert result["phases"] == []
        assert "No skill gaps" in result["learning_focus"]

    def test_single_skill(self):
        result = generate_roadmap([_MISSING_SKILLS[0]])
        assert result["total_skills"] == 1
        assert result["total_phases"] == 1
        assert result["phases"][0]["phase"] == 1

    def test_large_skill_list_creates_3_phases(self):
        # 13+ skills should fill all 3 phases
        large_list = [
            {"skill": f"Skill{i}", "count": 10 - i, "percentage": 90 - i * 5, "category": "tools"}
            for i in range(15)
        ]
        result = generate_roadmap(large_list)
        assert result["total_phases"] == 3

    def test_learning_focus_is_non_empty(self):
        result = generate_roadmap(_MISSING_SKILLS)
        assert result["learning_focus"]
        assert len(result["learning_focus"]) > 10

    def test_priority_score_in_each_skill(self):
        result = generate_roadmap(_MISSING_SKILLS)
        for phase in result["phases"]:
            for skill in phase["skills"]:
                assert "priority_score" in skill
                assert skill["priority_score"] > 0


class TestSkillRoadmapApi:
    @pytest_asyncio.fixture
    async def test_db(self):
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
    async def client(self, test_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_roadmap_returns_200(self, client):
        resp = await client.post("/api/market/roadmap", json={"missing_skills": _MISSING_SKILLS})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_roadmap_empty_missing_skills_400(self, client):
        resp = await client.post("/api/market/roadmap", json={"missing_skills": []})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_roadmap_response_structure(self, client):
        resp = await client.post("/api/market/roadmap", json={"missing_skills": _MISSING_SKILLS})
        data = resp.json()
        assert "phases" in data
        assert "total_skills" in data
        assert data["total_skills"] == len(_MISSING_SKILLS)

    @pytest.mark.asyncio
    async def test_roadmap_nonexistent_resume_404(self, client):
        resp = await client.post("/api/market/roadmap", json={
            "missing_skills": _MISSING_SKILLS,
            "resume_id": 9999,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_roadmap_phases_have_skills(self, client):
        resp = await client.post("/api/market/roadmap", json={"missing_skills": _MISSING_SKILLS})
        data = resp.json()
        for phase in data["phases"]:
            assert len(phase["skills"]) > 0
