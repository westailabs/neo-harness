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
    # Prefer low for thrift; gpt-5-mini may reject effort "none" on some builds
    copilot_effort: str = Field(default="low", alias="COPILOT_EFFORT")
    act_allow_tools: bool = Field(default=True, alias="NEO_ACT_ALLOW_TOOLS")
    provider_cwd: str | None = Field(default=None, alias="NEO_PROVIDER_CWD")
    # Named agent pack under agents/<id>/ (e.g. sysadmin)
    agent: str | None = Field(default=None, alias="NEO_AGENT")

    # Token diet / prompt budgets
    prompt_max_chars_plan: int = Field(default=4000, alias="NEO_PROMPT_MAX_CHARS_PLAN")
    prompt_max_chars_act: int = Field(default=3000, alias="NEO_PROMPT_MAX_CHARS_ACT")
    prompt_max_chars_reflect: int = Field(default=2500, alias="NEO_PROMPT_MAX_CHARS_REFLECT")
    episode_tail: int = Field(default=5, alias="NEO_EPISODE_TAIL")
    observation_tail: int = Field(default=3, alias="NEO_OBSERVATION_TAIL")
    # Skip interval reflection when plan is short and still progressing
    skip_interval_reflect_max_steps: int = Field(
        default=3, alias="NEO_SKIP_INTERVAL_REFLECT_MAX_STEPS"
    )
    task_display_chars: int = Field(default=120, alias="NEO_TASK_DISPLAY_CHARS")

    # Policy / InfoSec (see neo_harness.security.policy)
    policy_tier: str = Field(default="propose", alias="NEO_POLICY_TIER")
    path_allow: str = Field(default="", alias="NEO_PATH_ALLOW")
    path_deny: str = Field(default="", alias="NEO_PATH_DENY")
    # Redact secrets in memory / audit by default
    redact_secrets: bool = Field(default=True, alias="NEO_REDACT_SECRETS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
