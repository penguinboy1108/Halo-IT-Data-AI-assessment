from pathlib import Path

from agent.tools.duckdb_tool import run_read_only_query
from scripts.build_duckdb import build_database


def test_build_duckdb_and_query(tmp_path):
    db_path = tmp_path / "halo_test.duckdb"
    build_database(db_path=db_path)
    assert db_path.exists()
    result = run_read_only_query(
        "SELECT COUNT(*) AS ticket_count FROM tickets WHERE reporting_eligible_flag = TRUE",
        "Count reporting-eligible tickets",
        db_path=Path(db_path),
    )
    assert result.rows[0]["ticket_count"] == 67136
