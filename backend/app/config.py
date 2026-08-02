from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    DOSTT_API_BASE_URL: str = "https://testdostt.getlokalapp.com"
    GEMINI_MODEL: str = "gemini-3.5-flash"
    SESSION_TTL_SECONDS: int = 3600
    FAQ_FILE_PATH: str = str(Path(__file__).parent.parent / "data" / "faqs.json")
    MAX_RECENT_CALLS: int = 5
    MAX_RECENT_TRANSACTIONS: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
