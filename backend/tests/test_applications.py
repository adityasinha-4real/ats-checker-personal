"""Tests for Application Tracker (Feature 1 of v4.0)."""
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


_APP_PAYLOAD = {
    "company": "Acme Corp",
    "role": "Software Engineer",
    "date_applied": "2026-06-01",
    "status": "applied",
    "notes": "Applied via LinkedIn",
}


class TestApplicationCRUD:
    @pytest.mark.asyncio
    async def test_create_application(self, client):
        resp = await client.post("/api/applications", json=_APP_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["company"] == "Acme Corp"
        assert data["role"] == "Software Engineer"
        assert data["status"] == "applied"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_applications_empty(self, client):
        resp = await client.get("/api/applications")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_applications_after_create(self, client):
        await client.post("/api/applications", json=_APP_PAYLOAD)
        resp = await client.get("/api/applications")
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_get_application(self, client):
        create_resp = await client.post("/api/applications", json=_APP_PAYLOAD)
        app_id = create_resp.json()["id"]
        get_resp = await client.get(f"/api/applications/{app_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["company"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, client):
        resp = await client.get("/api/applications/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_status(self, client):
        create_resp = await client.post("/api/applications", json=_APP_PAYLOAD)
        app_id = create_resp.json()["id"]
        update_resp = await client.put(f"/api/applications/{app_id}", json={"status": "interview"})
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "interview"

    @pytest.mark.asyncio
    async def test_update_notes(self, client):
        create_resp = await client.post("/api/applications", json=_APP_PAYLOAD)
        app_id = create_resp.json()["id"]
        update_resp = await client.put(f"/api/applications/{app_id}", json={"notes": "Got a callback!"})
        assert update_resp.json()["notes"] == "Got a callback!"

    @pytest.mark.asyncio
    async def test_delete_application(self, client):
        create_resp = await client.post("/api/applications", json=_APP_PAYLOAD)
        app_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/applications/{app_id}")
        assert del_resp.status_code == 204
        get_resp = await client.get(f"/api/applications/{app_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, client):
        bad_payload = {**_APP_PAYLOAD, "status": "maybe"}
        resp = await client.post("/api/applications", json=bad_payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_all_valid_statuses_accepted(self, client):
        for s in ["applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"]:
            resp = await client.post("/api/applications", json={**_APP_PAYLOAD, "status": s})
            assert resp.status_code == 201, f"Status {s} was rejected"

    @pytest.mark.asyncio
    async def test_status_filter(self, client):
        await client.post("/api/applications", json={**_APP_PAYLOAD, "status": "applied"})
        await client.post("/api/applications", json={**_APP_PAYLOAD, "status": "interview"})
        resp = await client.get("/api/applications?status_filter=interview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "interview"

    @pytest.mark.asyncio
    async def test_default_values(self, client):
        resp = await client.post("/api/applications", json={"company": "X", "role": "Y"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "applied"
        assert data["notes"] == ""


class TestApplicationAnalytics:
    @pytest.mark.asyncio
    async def test_analytics_empty(self, client):
        resp = await client.get("/api/applications/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applications"] == 0
        assert data["conversion_rates"]["response_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_analytics_counts(self, client):
        await client.post("/api/applications", json={**_APP_PAYLOAD, "status": "applied"})
        await client.post("/api/applications", json={**_APP_PAYLOAD, "status": "interview"})
        await client.post("/api/applications", json={**_APP_PAYLOAD, "status": "offer"})
        resp = await client.get("/api/applications/analytics")
        data = resp.json()
        assert data["total_applications"] == 3
        assert data["by_status"]["applied"] == 1
        assert data["by_status"]["interview"] == 1
        assert data["by_status"]["offer"] == 1

    @pytest.mark.asyncio
    async def test_analytics_conversion_rates(self, client):
        # 4 apps: 1 applied, 1 phone_screen, 1 interview, 1 offer
        for s in ["applied", "phone_screen", "interview", "offer"]:
            await client.post("/api/applications", json={**_APP_PAYLOAD, "status": s})
        resp = await client.get("/api/applications/analytics")
        data = resp.json()
        rates = data["conversion_rates"]
        # responded = phone_screen + interview + offer = 3 out of 4
        assert rates["response_rate"] == 75.0
        # interviewed = interview + offer = 2 out of 4
        assert rates["interview_rate"] == 50.0
        # offer = 1 out of 4
        assert rates["offer_rate"] == 25.0

    @pytest.mark.asyncio
    async def test_analytics_required_keys(self, client):
        resp = await client.get("/api/applications/analytics")
        data = resp.json()
        assert "total_applications" in data
        assert "by_status" in data
        assert "conversion_rates" in data
        assert "variant_performance" in data
        assert "monthly_trend" in data

    @pytest.mark.asyncio
    async def test_analytics_monthly_trend(self, client):
        await client.post("/api/applications", json={**_APP_PAYLOAD, "date_applied": "2026-01-15"})
        await client.post("/api/applications", json={**_APP_PAYLOAD, "date_applied": "2026-01-20"})
        await client.post("/api/applications", json={**_APP_PAYLOAD, "date_applied": "2026-02-05"})
        resp = await client.get("/api/applications/analytics")
        trend = resp.json()["monthly_trend"]
        months = {t["month"]: t["count"] for t in trend}
        assert months.get("2026-01") == 2
        assert months.get("2026-02") == 1
