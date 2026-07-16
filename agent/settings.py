"""Runtime settings for the analytics agent."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Environment-backed settings.

    The app defaults to fake mode when GROQ_API_KEY is absent or left as the
    assessment placeholder. This keeps CI, Docker smoke tests, and demos
    deterministic without making live LLM calls.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    agent_llm_mode: Literal["auto", "fake", "groq"] = Field(default="auto", alias="AGENT_LLM_MODE")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
    temperature: float = Field(default=0.0, alias="AGENT_TEMPERATURE")
    max_completion_tokens: int = Field(default=2048, alias="AGENT_MAX_COMPLETION_TOKENS")
    max_retries: int = Field(default=1, alias="AGENT_MAX_RETRIES")
    max_rows: int = Field(default=200, alias="AGENT_MAX_ROWS")
    max_result_cells: int = Field(default=5000, alias="AGENT_MAX_RESULT_CELLS")
    query_timeout_seconds: int = Field(default=20, alias="AGENT_QUERY_TIMEOUT_SECONDS")
    db_path: Path = Field(default=ROOT / "data" / "processed" / "halo_analytics.duckdb")
    data_dir: Path = Field(default=ROOT / "data" / "processed")
    prompts_dir: Path = Field(default=ROOT / "agent" / "prompts")
    config_dir: Path = Field(default=ROOT / "agent" / "config")
    traces_dir: Path = Field(default=ROOT / "agent" / "evals" / "reports")
    audit_log_path: Path = Field(
        default=ROOT / ".runtime" / "agent_queries.jsonl", alias="AGENT_AUDIT_LOG_PATH"
    )
    developer_mode: bool = Field(default=False, alias="AGENT_DEVELOPER_MODE")

    @property
    def use_fake_llm(self) -> bool:
        if self.agent_llm_mode == "fake":
            return True
        if self.agent_llm_mode == "groq":
            return False
        return not self.groq_api_key or self.groq_api_key == "MyAPI"


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    return Settings()
