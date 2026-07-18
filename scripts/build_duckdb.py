"""Build the local DuckDB database from processed Part 1 outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.tools.schema_tool import approved_tables_and_columns, dataset_version  # noqa: E402

DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "halo_analytics.duckdb"


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def build_database(data_dir: Path = DEFAULT_DATA_DIR, db_path: Path = DEFAULT_DB_PATH) -> Path:
    tickets_path = data_dir / "tickets_cleaned.parquet"
    if not tickets_path.exists():
        raise FileNotFoundError(f"Missing {tickets_path}. Run python src/prepare_data.py first.")

    tables, columns = approved_tables_and_columns()
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        ticket_columns = ", ".join(_quote(col) for col in columns["tickets"])
        # Dynamic identifiers are restricted to the checked-in schema allowlist.
        create_tickets_sql = f"""
            CREATE TABLE tickets AS
            SELECT {ticket_columns}
            FROM read_parquet(?)
            """  # nosec
        con.execute(
            create_tickets_sql,
            [str(tickets_path)],
        )

        csv_tables = {
            "date_dimension": data_dir / "date_dimension.csv",
            "data_quality_summary": data_dir / "data_quality_summary.csv",
            "category_mapping": data_dir / "category_mapping.csv",
            "issue_taxonomy": data_dir / "issue_taxonomy.csv",
        }
        for table_name, path in csv_tables.items():
            if table_name not in tables:
                continue
            if not path.exists():
                raise FileNotFoundError(f"Missing {path}")
            # Dynamic table names are restricted to local csv_tables and the schema allowlist.
            create_table_sql = (
                f"CREATE TABLE {_quote(table_name)} AS SELECT * FROM read_csv_auto(?, header=true)"  # nosec
            )
            con.execute(
                create_table_sql,
                [str(path)],
            )

        con.execute(
            "CREATE TABLE dataset_metadata AS SELECT ? AS dataset_version",
            [dataset_version(data_dir)],
        )
        con.execute("CHECKPOINT")

    return db_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    output = build_database(args.data_dir, args.db_path)
    print(f"Built DuckDB database at {output}")


if __name__ == "__main__":
    main()
