from functools import lru_cache
from typing import List, Optional

from pydantic import AnyUrl, BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    environment: str = Field("development", env="ENVIRONMENT")

    database_url: AnyUrl = Field(..., env="DATABASE_URL")

    discord_client_id: str = Field(..., env="DISCORD_CLIENT_ID")
    discord_client_secret: str = Field(..., env="DISCORD_CLIENT_SECRET")
    discord_redirect_uri: AnyUrl = Field(..., env="DISCORD_REDIRECT_URI")
    discord_allowed_guild_ids: List[int] = Field(default_factory=list, env="DISCORD_GUILD_IDS")

    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(60, env="JWT_EXPIRE_MINUTES")

    api_base_path: str = Field("/api", env="API_BASE_PATH")

    cors_allow_origins: List[str] = Field(default_factory=list, env="CORS_ALLOW_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("discord_allowed_guild_ids", pre=True)
    def _parse_guild_ids(cls, value):  # type: ignore[override]
        if isinstance(value, list):
            return [int(v) for v in value]
        if isinstance(value, str) and value.strip():
            return [int(v.strip()) for v in value.split(",")]
        raise ValueError("DISCORD_GUILD_IDS must include at least one guild id.")

    @validator("cors_allow_origins", pre=True)
    def _parse_origins(cls, value):  # type: ignore[override]
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [v.strip() for v in str(value).split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()

