from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "sqlite:///./mpesa_tracker.db"
    slack_webhook_url: str = ""
    daily_limit: float = 2000.0
    warning_threshold: float = 0.7
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
