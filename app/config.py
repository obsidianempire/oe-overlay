from functools import lru_cache
from typing import List

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")

    database_url: str = Field(..., alias="DATABASE_URL")

    discord_client_id: str = Field(..., alias="DISCORD_CLIENT_ID")
    discord_client_secret: str = Field(..., alias="DISCORD_CLIENT_SECRET")
    discord_redirect_uri: AnyUrl = Field(..., alias="DISCORD_REDIRECT_URI")
    discord_allowed_guild_ids: List[int] = Field(default_factory=lambda: [1119640635817853028])

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    api_base_path: str = Field(default="/api", alias="API_BASE_PATH")

    cors_allow_origins_raw: str | List[str] | None = Field(default=None, alias="CORS_ALLOW_ORIGINS")

    @property
    def cors_allow_origins(self) -> List[str]:
        if self.cors_allow_origins_raw in (None, "", []):
            return []
        if isinstance(self.cors_allow_origins_raw, list):
            return [str(origin).strip() for origin in self.cors_allow_origins_raw if str(origin).strip()]
        return [origin.strip() for origin in str(self.cors_allow_origins_raw).split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
