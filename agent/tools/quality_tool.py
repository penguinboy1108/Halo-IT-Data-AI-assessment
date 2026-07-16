"""Data-quality context tool."""

from __future__ import annotations

import csv
from typing import Any

from agent.settings import Settings, get_settings


def get_data_quality_context(
    topics: list[str] | None = None, settings: Settings | None = None
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    path = settings.data_dir / "data_quality_summary.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not topics:
        return rows
    needles = {topic.lower() for topic in topics}
    return [
        row
        for row in rows
        if any(
            needle in row.get("metric", "").lower() or needle in row.get("notes", "").lower()
            for needle in needles
        )
    ]
