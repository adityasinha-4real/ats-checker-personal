"""Tests for Feature 3: Multi-Resume Management (variants)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.database import Base, get_db

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


_VARIANT_PAYLOAD = {
    "name": "Backend Resume",
    "variant_type": "backend",
    "content": {
        "skills": {"primary": ["python", "django", "postgresql"], "secondary": ["docker"], "all": ["python", "django", "postgresql", "docker"]},
        "projects": [{"original": "Built REST API", "optimized": "Built REST API", "safety": "SAFE"}],
    },
    "description": "Tailored for backend roles",
}


class TestVariantCRUD:
    @pytest.mark.asyncio
    async def test_create_variant(self, client):
        response = await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Backend Resume"
        assert data["variant_type"] == "backend"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_variants_empty(self, client):
        response = await client.get("/api/variants")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_variants_after_create(self, client):
        await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        response = await client.get("/api/variants")
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_get_variant(self, client):
        create_resp = await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        variant_id = create_resp.json()["id"]
        get_resp = await client.get(f"/api/variants/{variant_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Backend Resume"

    @pytest.mark.asyncio
    async def test_get_nonexistent_variant(self, client):
        response = await client.get("/api/variants/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_variant_name(self, client):
        create_resp = await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        variant_id = create_resp.json()["id"]
        update_resp = await client.put(f"/api/variants/{variant_id}", json={"name": "Senior Backend Resume"})
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Senior Backend Resume"

    @pytest.mark.asyncio
    async def test_update_description(self, client):
        create_resp = await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        variant_id = create_resp.json()["id"]
        update_resp = await client.put(f"/api/variants/{variant_id}", json={"description": "Updated desc"})
        assert update_resp.json()["description"] == "Updated desc"

    @pytest.mark.asyncio
    async def test_delete_variant(self, client):
        create_resp = await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        variant_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/variants/{variant_id}")
        assert del_resp.status_code == 204
        get_resp = await client.get(f"/api/variants/{variant_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_variant_type_rejected(self, client):
        bad_payload = {**_VARIANT_PAYLOAD, "variant_type": "invalid_type"}
        response = await client.post("/api/variants", json=bad_payload)
        assert response.status_code == 400


class TestVariantDuplicate:
    @pytest.mark.asyncio
    async def test_duplicate_creates_copy(self, client):
        create_resp = await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        variant_id = create_resp.json()["id"]
        dup_resp = await client.post(f"/api/variants/{variant_id}/duplicate")
        assert dup_resp.status_code == 201
        dup = dup_resp.json()
        assert dup["id"] != variant_id
        assert "(copy)" in dup["name"]

    @pytest.mark.asyncio
    async def test_duplicate_preserves_content(self, client):
        create_resp = await client.post("/api/variants", json=_VARIANT_PAYLOAD)
        variant_id = create_resp.json()["id"]
        dup_resp = await client.post(f"/api/variants/{variant_id}/duplicate")
        dup = dup_resp.json()
        assert dup["variant_type"] == "backend"
        assert dup["content"] == _VARIANT_PAYLOAD["content"]

    @pytest.mark.asyncio
    async def test_duplicate_nonexistent(self, client):
        response = await client.post("/api/variants/9999/duplicate")
        assert response.status_code == 404


class TestVariantRecommend:
    @pytest.mark.asyncio
    async def test_recommend_requires_jd(self, client):
        response = await client.post("/api/variants/recommend", json={})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_recommend_no_variants(self, client):
        response = await client.post("/api/variants/recommend", json={"jd_text": "Python developer"})
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_recommend_returns_best_match(self, client):
        # Create two variants with different skills
        await client.post("/api/variants", json={
            "name": "Python Variant",
            "variant_type": "backend",
            "content": {"skills": {"all": ["python", "django", "postgresql"]}},
        })
        await client.post("/api/variants", json={
            "name": "JS Variant",
            "variant_type": "frontend",
            "content": {"skills": {"all": ["javascript", "react", "css"]}},
        })
        response = await client.post("/api/variants/recommend", json={
            "jd_text": "We need a Python developer with Django and PostgreSQL."
        })
        assert response.status_code == 200
        data = response.json()
        assert "recommended" in data
        assert "match_score" in data
        assert data["recommended"]["name"] == "Python Variant"

    @pytest.mark.asyncio
    async def test_recommend_returns_all_scores(self, client):
        await client.post("/api/variants", json={**_VARIANT_PAYLOAD, "name": "V1"})
        await client.post("/api/variants", json={**_VARIANT_PAYLOAD, "name": "V2", "variant_type": "fullstack"})
        response = await client.post("/api/variants/recommend", json={"jd_text": "Python backend developer"})
        data = response.json()
        assert len(data["all_scores"]) == 2

    @pytest.mark.asyncio
    async def test_valid_variant_types(self, client):
        for vtype in ["master", "fullstack", "ai", "custom"]:
            resp = await client.post("/api/variants", json={**_VARIANT_PAYLOAD, "variant_type": vtype, "name": f"{vtype} resume"})
            assert resp.status_code == 201
