from pydantic_settings import BaseSettings
from pathlib import Path


_DOSTT_BASE_STAGING    = "https://testdostt.getlokalapp.com"
_DOSTT_BASE_PRODUCTION = "https://api.dostt.in"


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"
    SESSION_TTL_SECONDS: int = 3600
    APP_ENV: str = "production"  # "staging" or "production"
    DUMMY_MODE: bool = False
    MAX_RECENT_CALLS: int = 5
    MAX_RECENT_TRANSACTIONS: int = 5

    @property
    def DOSTT_API_BASE_URL(self) -> str:
        return _DOSTT_BASE_PRODUCTION if self.APP_ENV == "production" else _DOSTT_BASE_STAGING

    @property
    def FAQ_FILE_PATH(self) -> str:
        filename = "faq-stag.json" if self.APP_ENV == "staging" else "faqs.json"
        return str(Path(__file__).parent.parent / "data" / filename)

    class Config:
        env_file = ".env"


settings = Settings()
