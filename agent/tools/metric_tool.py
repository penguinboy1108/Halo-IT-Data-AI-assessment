"""Metric registry access."""

from __future__ import annotations

from typing import Any, cast

from agent.settings import Settings, get_settings
from agent.tools.config_loader import load_yaml


def get_metric_registry(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return cast(dict[str, Any], load_yaml(settings.config_dir / "metrics.yaml")["metrics"])


def get_metric_definitions(
    metric_names: list[str] | None = None, settings: Settings | None = None
) -> dict[str, Any]:
    registry = get_metric_registry(settings)
    if not metric_names:
        return registry
    return {name: registry[name] for name in metric_names if name in registry}


def metric_sql(name: str, settings: Settings | None = None) -> str:
    registry = get_metric_registry(settings)
    return str(registry[name]["sql_expression"]).strip()


def metric_filters(name: str, settings: Settings | None = None) -> list[str]:
    registry = get_metric_registry(settings)
    return [str(item) for item in registry[name].get("default_filters", [])]
