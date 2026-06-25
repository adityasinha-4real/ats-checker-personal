from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "ats.db"


class Settings(BaseSettings):
    app_name: str = "ATS Checker"
    debug: bool = True
    database_url: str = f"sqlite+aiosqlite:///{DB_PATH}"
    upload_dir: Path = UPLOADS_DIR
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = ["pdf", "docx"]
    spacy_model: str = "en_core_web_sm"
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    cors_origins_str: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_str.split(",")]

    # Scoring weights
    keyword_weight: float = 0.35
    skills_weight: float = 0.25
    experience_weight: float = 0.15
    education_weight: float = 0.10
    semantic_weight: float = 0.15

    model_config = {"env_file": ".env"}


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
