from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trade Intelligence Hub"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./tradehub.db"
    redis_url: str = "redis://localhost:6379/0"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    seed_demo_data: bool = True
    secret_key: str = "market-decision-ai-dev-secret"
    api_admin_token: str = "admin-local-token"
    api_analyst_token: str = "analyst-local-token"
    oanda_api_key: str = ""
    oanda_account_id: str = ""
    oanda_base_url: str = "https://api-fxpractice.oanda.com"
    collector_poll_seconds: int = 30
    macro_poll_seconds: int = 120
    redis_live_board_channel: str = "market:live_board"
    redis_macro_channel: str = "market:macro"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
