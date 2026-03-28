from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str | None = None
    api_secret: str = "dev-change-me"
    market: str = "NSE"
    universe: str = "NIFTY50"
    broker_mode: str = "paper"  # paper | live

    # Groww Trade API — use GROWW_AUTH_TOKEN (JWT from Groww), not API_SECRET
    groww_auth_token: str | None = None
    groww_instruments_json: str = "[]"
    # Legacy: if true, allows place (same as mutations). Prefer GROWW_ALLOW_BROKER_MUTATIONS.
    groww_allow_place_order: bool = False
    groww_allow_broker_mutations: bool = False
    groww_ltp_wait_seconds: float = 2.0

    # Pre-trade risk (static caps — tune before live)
    risk_max_order_quantity: int = 100
    risk_max_orders_per_day: int = 20
    risk_max_notional_per_order: float = 0.0  # 0 = disabled
    risk_require_limit_price: bool = True  # blocks MARKET when true

    # Hugging Face Inference API (optional — token via env only, never commit)
    huggingface_api_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "HUGGINGFACE_API_TOKEN",
            "HF_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
        ),
    )
    hf_inference_model: str = "ProsusAI/finbert"
    hf_enable_in_pipeline: bool = False
    hf_max_symbols_per_tick: int = 3

    @field_validator("groww_instruments_json", mode="before")
    @classmethod
    def strip_instruments(cls, v: object) -> str:
        if v is None:
            return "[]"
        return str(v).strip() or "[]"


@lru_cache
def get_settings() -> Settings:
    return Settings()
