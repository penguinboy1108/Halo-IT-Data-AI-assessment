"""YAML configuration loading helpers."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache
def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data
