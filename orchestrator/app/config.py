from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str | None = None
    api_secret: str = "dev-change-me"
    market: str = "NSE"
    universe: str = "NIFTY50"
    broker_mode: str = "paper"  # paper | live


@lru_cache
def get_settings() -> Settings:
    return Settings()
