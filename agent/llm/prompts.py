"""Prompt registry and loading helpers."""

from __future__ import annotations

from typing import Any, cast

from agent.settings import Settings, get_settings
from agent.tools.config_loader import load_yaml


def prompt_registry(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return cast(dict[str, Any], load_yaml(settings.config_dir / "prompts.yaml")["prompts"])


def load_prompt(role: str, settings: Settings | None = None) -> tuple[str, str]:
    settings = settings or get_settings()
    registry = prompt_registry(settings)
    prompt = registry[role]
    prompt_path = settings.prompts_dir / str(prompt["file"])
    return prompt_path.read_text(encoding="utf-8"), str(prompt["active_version"])


def prompt_versions(settings: Settings | None = None) -> dict[str, str]:
    registry = prompt_registry(settings)
    return {role: str(config["active_version"]) for role, config in registry.items()}
