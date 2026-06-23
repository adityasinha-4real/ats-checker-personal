"""API integration tests using httpx AsyncClient."""
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


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_jd(client):
    payload = {
        "title": "Python Developer",
        "company": "TechCorp",
        "description": "We need a Python developer with FastAPI and Docker experience. 3 years minimum. Bachelor degree required.",
    }
    response = await client.post("/api/job-descriptions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Python Developer"
    assert data["company"] == "TechCorp"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_jds_empty(client):
    response = await client.get("/api/job-descriptions")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_and_get_jd(client):
    payload = {"title": "SWE", "company": "Acme", "description": "Python developer needed with 2 years experience."}
    create_resp = await client.post("/api/job-descriptions", json=payload)
    jd_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/job-descriptions/{jd_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == jd_id


@pytest.mark.asyncio
async def test_update_jd(client):
    payload = {"title": "SWE", "company": "Acme", "description": "Python developer with 2 years experience."}
    create_resp = await client.post("/api/job-descriptions", json=payload)
    jd_id = create_resp.json()["id"]

    update_resp = await client.put(f"/api/job-descriptions/{jd_id}", json={"title": "Senior SWE"})
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Senior SWE"


@pytest.mark.asyncio
async def test_delete_jd(client):
    payload = {"title": "SWE", "company": "Acme", "description": "Python developer with experience."}
    create_resp = await client.post("/api/job-descriptions", json=payload)
    jd_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/job-descriptions/{jd_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/job-descriptions/{jd_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_resumes_empty(client):
    response = await client.get("/api/resumes")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_nonexistent_resume(client):
    response = await client.get("/api/resumes/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_analyses_empty(client):
    response = await client.get("/api/analysis")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_dashboard_stats(client):
    response = await client.get("/api/analysis/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_resumes" in data
    assert "total_jds" in data
    assert "total_analyses" in data
    assert data["total_resumes"] == 0


@pytest.mark.asyncio
async def test_run_analysis_missing_resume(client):
    payload = {
        "resume_id": 99999,
        "jd_text": "Python developer with 2 years experience needed.",
    }
    response = await client.post("/api/analysis/run", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_invalid_file(client):
    files = {"files": ("test.txt", b"Hello World", "text/plain")}
    response = await client.post("/api/resumes/upload", files=files)
    assert response.status_code == 400
