"""Application settings and environment configuration."""
import os
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Load .env if present
load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    """Application configuration loaded from environment variables with safe defaults."""

    # Project metadata
    APP_NAME: str = os.getenv("APP_NAME", "AI MCQ Generator & Smart Quiz Platform")
    VERSION: str = "1.0.0"
    BASE_DIR: Path = BASE_DIR
    TEMP_DIR: Path = BASE_DIR / "temp_uploads"

    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    API_TIMEOUT_SECONDS: int = int(os.getenv("API_TIMEOUT_SECONDS", "60"))
    RATE_LIMIT_RETRIES: int = int(os.getenv("RATE_LIMIT_RETRIES", "3"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'quiz_platform.db'}")

    # Upload and processing limits
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Quiz Generation Options
    ALLOWED_QUESTION_COUNTS: Tuple[int, ...] = (10, 20, 30, 50)
    DEFAULT_QUESTION_COUNT: int = int(os.getenv("DEFAULT_QUESTION_COUNT", "50"))
    MAX_QUESTION_COUNT: int = int(os.getenv("MAX_QUESTION_COUNT", "50"))
    DIFFICULTY_LEVELS: Tuple[str, ...] = ("Easy", "Medium", "Hard", "Mixed")

    # Chunking & Context Window Management for Long PDFs
    CHUNK_SIZE_CHARS: int = 3500
    CHUNK_OVERLAP_CHARS: int = 350
    MAX_DOCUMENT_CHARS_TO_SEND: int = 70000

    @property
    def has_gemini_api_key(self) -> bool:
        """Check if a valid Gemini API key is configured."""
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY != "your_gemini_api_key_here")

    def reload(self) -> None:
        """Reload environment variables from disk."""
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()


settings = Settings()
# Ensure temp dir exists
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
