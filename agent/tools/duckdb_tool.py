"""Read-only DuckDB execution tool."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import duckdb

from agent.models import QueryResult
from agent.settings import Settings, get_settings
from agent.tools.schema_tool import dataset_version


def run_read_only_query(
    sql: str,
    purpose: str,
    *,
    max_rows: int = 200,
    db_path: Path | None = None,
    settings: Settings | None = None,
) -> QueryResult:
    del purpose
    settings = settings or get_settings()
    db_path = db_path or settings.db_path
    if not db_path.exists():
        raise FileNotFoundError(
            f"DuckDB database not found: {db_path}. Run python scripts/build_duckdb.py"
        )

    start = time.perf_counter()
    sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]
    query_id = f"qry_{sql_hash}"

    with duckdb.connect(str(db_path), read_only=True) as con:
        con.execute("SET enable_progress_bar=false")
        count_row = con.execute("SELECT COUNT(*) FROM tickets").fetchone()
        source_row_count = 0 if count_row is None else int(count_row[0])
        relation = con.execute(sql)
        columns = [item[0] for item in relation.description or []]
        max_columns = max(len(columns), 1)
        max_rows_by_cells = max(1, settings.max_result_cells // max_columns)
        effective_max_rows = min(max_rows, settings.max_rows, max_rows_by_cells)
        raw_rows = relation.fetchmany(effective_max_rows + 1)

    truncated = len(raw_rows) > effective_max_rows
    rows = raw_rows[:effective_max_rows]
    records = [dict(zip(columns, row, strict=False)) for row in rows]
    execution_ms = int((time.perf_counter() - start) * 1000)
    return QueryResult(
        query_id=query_id,
        columns=columns,
        rows=records,
        row_count=len(records),
        source_row_count=source_row_count,
        execution_ms=execution_ms,
        truncated=truncated,
        dataset_version=dataset_version(settings.data_dir),
        sql_hash=sql_hash,
    )


def table_exists(db_path: Path, table_name: str) -> bool:
    if not db_path.exists():
        return False
    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute("SHOW TABLES").fetchall()
    return (table_name,) in rows
