"""Environment-backed runtime configuration."""

from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    app_version = "3.0.0"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
    ai_timeout_seconds: float = float(os.getenv("AI_TIMEOUT_SECONDS", "20"))
    cache_db_path: Path = PROJECT_ROOT / os.getenv(
        "CACHE_DB_PATH", "data/winevent_analyzer.db"
    )
    prompt_version: str = os.getenv("PROMPT_VERSION", "v1").strip()

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
