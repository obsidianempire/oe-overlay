from functools import lru_cache
from typing import List

from pydantic import AnyUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    environment: str = Field("development", env="ENVIRONMENT")

    database_url: str = Field(..., env="DATABASE_URL")

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

    @field_validator("discord_allowed_guild_ids", mode="before")
    def _parse_guild_ids(cls, value):  # type: ignore[override]
        if isinstance(value, list):
            return [int(v) for v in value]
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            return [int(v.strip()) for v in value.split(",") if v.strip()]
        return value

    @field_validator("cors_allow_origins", mode="before")
    def _parse_origins(cls, value):  # type: ignore[override]
        if value in (None, "", []):
            return []
        if isinstance(value, list):
            return value
        return [v.strip() for v in str(value).split(",")]

    @model_validator(mode="after")
    def _ensure_guilds(self) -> "Settings":
        if not self.discord_allowed_guild_ids:
            raise ValueError("DISCORD_GUILD_IDS must include at least one guild id.")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
