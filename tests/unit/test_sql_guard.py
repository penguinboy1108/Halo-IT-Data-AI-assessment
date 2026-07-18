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


def test_sql_guard_allows_safe_cte_alias():
    result = validate_sql(
        """
        WITH base AS (
          SELECT
            reporting_category,
            CASE WHEN calculated_sla_breached THEN 1 ELSE 0 END AS sla_breached,
            CASE
              WHEN is_closed_ticket
                AND valid_resolved_date_flag
                AND resolution_time_hours IS NOT NULL
                AND sla_target_hours IS NOT NULL
              THEN 1 ELSE 0
            END AS closed_valid
          FROM tickets
          WHERE reporting_eligible_flag = TRUE
            AND reporting_period_flag = TRUE
        )
        SELECT
          reporting_category,
          COUNT(*) AS total_tickets,
          1.0 - (SUM(sla_breached)::DOUBLE / NULLIF(SUM(closed_valid), 0))
            AS sla_compliance_rate
        FROM base
        GROUP BY reporting_category
        ORDER BY total_tickets DESC, sla_compliance_rate ASC
        LIMIT 10
        """
    )
    assert result.approved


def test_sql_guard_allows_safe_physical_table_alias():
    result = validate_sql(
        """
        SELECT t.team, COUNT(*) AS ticket_count
        FROM tickets AS t
        WHERE t.reporting_eligible_flag = TRUE
        GROUP BY t.team
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


def test_sql_guard_rejects_unapproved_personal_column_hidden_in_cte():
    result = validate_sql(
        """
        WITH base AS (
          SELECT customer_email AS segment
          FROM tickets
        )
        SELECT segment, COUNT(*) AS ticket_count
        FROM base
        GROUP BY segment
        LIMIT 10
        """
    )
    assert not result.approved


def test_sql_guard_rejects_multiple_statements():
    result = validate_sql("SELECT ticket_id FROM tickets LIMIT 1; DROP TABLE tickets")
    assert not result.approved


def test_sql_guard_rejects_environment_function():
    result = validate_sql("SELECT getenv('GROQ_API_KEY')")
    assert not result.approved


def test_sql_guard_rejects_too_many_ctes():
    result = validate_sql(
        """
        WITH
          a AS (SELECT ticket_id FROM tickets LIMIT 1),
          b AS (SELECT ticket_id FROM tickets LIMIT 1),
          c AS (SELECT ticket_id FROM tickets LIMIT 1),
          d AS (SELECT ticket_id FROM tickets LIMIT 1),
          e AS (SELECT ticket_id FROM tickets LIMIT 1)
        SELECT ticket_id FROM e
        """
    )
    assert not result.approved
