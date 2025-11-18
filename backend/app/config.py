from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Keyword Recommendation API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "keyword_recommendation"

    # NLP settings
    SPACY_MODEL: str = "en_core_web_sm"  # Use en_core_web_lg for better accuracy
    MAX_KEYWORDS: int = 10
    MIN_KEYWORD_SCORE: float = 0.3

    # Scraping settings
    REQUEST_TIMEOUT: int = 30
    MAX_CONTENT_LENGTH: int = 100000  # characters

    # Recommendation settings
    MAX_RECOMMENDATIONS: int = 10
    FUZZY_MATCH_THRESHOLD: float = 0.6

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
