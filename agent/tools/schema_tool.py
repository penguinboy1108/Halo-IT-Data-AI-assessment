"""Approved schema discovery."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from agent.settings import Settings, get_settings
from agent.tools.config_loader import load_yaml

DATASET_FILES = [
    "tickets_cleaned.parquet",
    "date_dimension.csv",
    "data_quality_summary.csv",
    "category_mapping.csv",
    "issue_taxonomy.csv",
]


def dataset_version(data_dir: Path) -> str:
    hasher = hashlib.sha256()
    for name in DATASET_FILES:
        path = data_dir / name
        hasher.update(name.encode("utf-8"))
        if path.exists():
            hasher.update(str(path.stat().st_size).encode("ascii"))
            hasher.update(str(int(path.stat().st_mtime)).encode("ascii"))
            with path.open("rb") as handle:
                hasher.update(handle.read(1024 * 1024))
    return hasher.hexdigest()[:16]


def get_dataset_schema(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    allowlist = load_yaml(settings.config_dir / "schema_allowlist.yaml")
    tables = []
    for table_name, table in allowlist["dataset"]["tables"].items():
        tables.append(
            {
                "name": table_name,
                "description": table.get("description", ""),
                "columns": [
                    {"name": column_name, "description": description}
                    for column_name, description in table["columns"].items()
                ],
            }
        )
    return {"dataset_version": dataset_version(settings.data_dir), "tables": tables}


def approved_tables_and_columns(
    settings: Settings | None = None,
) -> tuple[set[str], dict[str, set[str]]]:
    settings = settings or get_settings()
    allowlist = load_yaml(settings.config_dir / "schema_allowlist.yaml")
    tables: set[str] = set()
    columns: dict[str, set[str]] = {}
    for table_name, table in allowlist["dataset"]["tables"].items():
        tables.add(table_name)
        columns[table_name] = set(table["columns"].keys())
    return tables, columns


def approved_column_names(settings: Settings | None = None) -> set[str]:
    _, columns = approved_tables_and_columns(settings)
    names: set[str] = set()
    for table_columns in columns.values():
        names.update(table_columns)
    return names
