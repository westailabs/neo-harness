"""Settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")

    provider: str = Field(default="mock", alias="NEO_PROVIDER")
    max_steps: int = Field(default=50, alias="NEO_MAX_STEPS")
    max_tokens: int = Field(default=200_000, alias="NEO_MAX_TOKENS")
    reflect_every_n: int = Field(default=3, alias="NEO_REFLECT_EVERY_N")
    loop_iterations: int = Field(default=20, alias="NEO_LOOP_ITERATIONS")

    xai_api_key: str | None = Field(default=None, alias="XAI_API_KEY")
    grok_build_cmd: str | None = Field(default=None, alias="GROK_BUILD_CMD")
    grok_model: str | None = Field(default=None, alias="GROK_MODEL")
    copilot_cmd: str | None = Field(default=None, alias="COPILOT_CMD")
    copilot_model: str | None = Field(default=None, alias="COPILOT_MODEL")
    copilot_effort: str = Field(default="low", alias="COPILOT_EFFORT")
    act_allow_tools: bool = Field(default=True, alias="NEO_ACT_ALLOW_TOOLS")
    provider_cwd: str | None = Field(default=None, alias="NEO_PROVIDER_CWD")


@lru_cache
def get_settings() -> Settings:
    return Settings()
