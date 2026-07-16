from agent.tools.sql_guard import validate_sql


def test_sql_guard_allows_safe_select():
    result = validate_sql(
        """
        SELECT team, COUNT(*) AS ticket_count
        FROM tickets
        WHERE reporting_eligible_flag = TRUE
        GROUP BY team
        ORDER BY ticket_count DESC
        LIMIT 10
        """
    )
    assert result.approved


def test_sql_guard_rejects_destructive_sql():
    result = validate_sql("DROP TABLE tickets")
    assert not result.approved


def test_sql_guard_rejects_wildcard():
    result = validate_sql("SELECT * FROM tickets LIMIT 10")
    assert not result.approved


def test_sql_guard_rejects_file_functions():
    result = validate_sql("SELECT read_csv_auto('/etc/passwd')")
    assert not result.approved


def test_sql_guard_rejects_unapproved_personal_column():
    result = validate_sql("SELECT customer_email FROM tickets LIMIT 10")
    assert not result.approved


def test_sql_guard_rejects_multiple_statements():
    result = validate_sql("SELECT ticket_id FROM tickets LIMIT 1; DROP TABLE tickets")
    assert not result.approved
