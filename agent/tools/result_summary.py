"""Compact deterministic summaries for query results."""

from __future__ import annotations

from statistics import mean, median
from typing import Any

from agent.models import QueryResult


def summarise_query_result(result: QueryResult) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "row_count": result.row_count,
        "columns": result.columns,
        "truncated": result.truncated,
    }
    numeric_columns: dict[str, list[float]] = {}
    for column in result.columns:
        values: list[float] = []
        for row in result.rows:
            value = row.get(column)
            if isinstance(value, bool) or value is None:
                continue
            if isinstance(value, int | float):
                values.append(float(value))
        if values:
            numeric_columns[column] = values
    summary["numeric"] = {
        column: {
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
            "median": median(values),
        }
        for column, values in numeric_columns.items()
    }
    summary["preview_rows"] = result.rows[:10]
    return summary
