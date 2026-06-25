from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import sys

from app.config import settings, DATA_DIR
from app.models.database import init_db
from app.routers import resumes, job_descriptions, analysis, rankings, exports, intelligence, optimizer, variants, market, applications

logger.remove()
logger.add(sys.stderr, format="{time:HH:mm:ss} | {level:<8} | {message}", level="INFO")
logger.add(str(DATA_DIR / "app.log"), rotation="10 MB", retention="7 days", level="DEBUG")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Application Optimizer API v4.0...")
    await init_db()
    logger.info("Database initialised")
    # Feature 7: preload sentence-transformer model so it is ready before analysis
    try:
        from app.services.nlp_engine import get_sentence_transformer
        import threading
        def _preload():
            model = get_sentence_transformer()
            if model:
                logger.info("Sentence-transformer model preloaded successfully")
            else:
                logger.warning("Sentence-transformer not available — semantic scoring will use fallback")
        threading.Thread(target=_preload, daemon=True).start()
    except Exception as e:
        logger.warning(f"Model preload skipped: {e}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Application Optimizer API",
    description="Personal Job Search Operating System - local, no cloud, no paid APIs",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router, prefix="/api")
app.include_router(job_descriptions.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(rankings.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(optimizer.router, prefix="/api")
app.include_router(variants.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(applications.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
