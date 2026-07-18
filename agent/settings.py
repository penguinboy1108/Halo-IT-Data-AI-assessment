"""Runtime settings for the analytics agent."""

import os
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _safe_resolve(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _candidate_and_parents(path: Path) -> Iterator[Path]:
    resolved = _safe_resolve(path)
    yield resolved
    yield from resolved.parents


def _looks_like_project_root(path: Path) -> bool:
    return (path / "agent" / "config").exists() and (
        (path / "data").exists() or (path / "scripts" / "build_duckdb.py").exists()
    )


def resolve_project_root(
    *,
    cwd: Path | None = None,
    package_root: Path | None = None,
    env_root: str | None = None,
) -> Path:
    """Resolve the repo root even when the package is imported from site-packages."""

    explicit_root = env_root if env_root is not None else os.getenv("AGENT_PROJECT_ROOT")
    if explicit_root:
        return _safe_resolve(Path(explicit_root))

    search_roots = [
        cwd or Path.cwd(),
        package_root or Path(__file__).resolve().parents[1],
    ]
    for search_root in search_roots:
        for candidate in _candidate_and_parents(search_root):
            if _looks_like_project_root(candidate):
                return candidate

    return _safe_resolve(package_root or Path(__file__).resolve().parents[1])


ROOT = resolve_project_root()


class Settings(BaseSettings):
    """Environment-backed settings.

    The app defaults to fake mode unless AGENT_LLM_MODE=groq is explicitly set.
    This keeps CI, Docker smoke tests, and demos deterministic without making
    live LLM calls even when a developer has a local key in .env.
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
    db_path: Path = Field(
        default=ROOT / "data" / "processed" / "halo_analytics.duckdb", alias="AGENT_DB_PATH"
    )
    data_dir: Path = Field(default=ROOT / "data" / "processed", alias="AGENT_DATA_DIR")
    prompts_dir: Path = Field(default=ROOT / "agent" / "prompts", alias="AGENT_PROMPTS_DIR")
    config_dir: Path = Field(default=ROOT / "agent" / "config", alias="AGENT_CONFIG_DIR")
    traces_dir: Path = Field(default=ROOT / "agent" / "evals" / "reports", alias="AGENT_TRACES_DIR")
    audit_log_path: Path = Field(
        default=ROOT / ".runtime" / "agent_queries.jsonl", alias="AGENT_AUDIT_LOG_PATH"
    )
    developer_mode: bool = Field(default=False, alias="AGENT_DEVELOPER_MODE")

    @property
    def use_fake_llm(self) -> bool:
        return self.agent_llm_mode != "groq"


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    return Settings()
