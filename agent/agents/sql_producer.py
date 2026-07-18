"""SQL producer role."""

from __future__ import annotations

from agent.models import AnalysisPlan, SQLCandidate
from agent.settings import Settings, get_settings


class SQLProducerAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def produce(self, plan: AnalysisPlan, feedback: str | None = None) -> SQLCandidate:
        del feedback
        if plan.intent == "data_quality":
            sql = """
            SELECT metric, value, percentage_of_tickets, notes
            FROM data_quality_summary
            ORDER BY metric
            LIMIT 50
            """
            return SQLCandidate(
                sql=sql,
                purpose="Summarise data quality limitations.",
                tables_used=["data_quality_summary"],
                columns_used=["metric", "value", "percentage_of_tickets", "notes"],
                metrics_used=[],
                expected_columns=["metric", "value", "percentage_of_tickets", "notes"],
                detail_query=True,
                max_rows=50,
            )
        if "holiday_period" in plan.dimensions:
            sql = """
            SELECT
              holiday_period,
              COUNT(*) AS ticket_count,
              MEDIAN(first_response_time_hours) AS median_first_response_hours,
              1.0 - (
                SUM(CASE WHEN calculated_sla_breached THEN 1 ELSE 0 END)::DOUBLE
                / NULLIF(COUNT(*), 0)
              ) AS sla_compliance_rate
            FROM tickets
            WHERE reporting_eligible_flag = TRUE
              AND is_closed_ticket = TRUE
              AND valid_resolved_date_flag = TRUE
            GROUP BY holiday_period
            ORDER BY ticket_count DESC
            """
            return SQLCandidate(
                sql=sql,
                purpose="Compare holiday-period ticket volume, response time, and SLA compliance.",
                tables_used=["tickets"],
                columns_used=[
                    "holiday_period",
                    "first_response_time_hours",
                    "calculated_sla_breached",
                    "reporting_eligible_flag",
                    "is_closed_ticket",
                    "valid_resolved_date_flag",
                ],
                metrics_used=[
                    "total_tickets",
                    "median_first_response_hours",
                    "sla_compliance_rate",
                ],
                expected_columns=[
                    "holiday_period",
                    "ticket_count",
                    "median_first_response_hours",
                    "sla_compliance_rate",
                ],
                detail_query=False,
                max_rows=20,
            )
        if "created_month" in plan.dimensions:
            sql = """
            SELECT
              created_month,
              created_month_name,
              COUNT(*) AS ticket_count
            FROM tickets
            WHERE reporting_eligible_flag = TRUE
              AND created_year = 2024
            GROUP BY created_month, created_month_name
            ORDER BY created_month ASC
            """
            return SQLCandidate(
                sql=sql,
                purpose="Monthly ticket volume trend for 2024.",
                tables_used=["tickets"],
                columns_used=[
                    "created_month",
                    "created_month_name",
                    "reporting_eligible_flag",
                    "created_year",
                ],
                metrics_used=["total_tickets"],
                expected_columns=["created_month", "created_month_name", "ticket_count"],
                detail_query=False,
                max_rows=20,
            )
        if "service_area" in plan.dimensions:
            sql = """
            SELECT
              service_area,
              COUNT(*) AS ticket_count,
              AVG(csat_score) AS average_csat,
              SUM(CASE WHEN is_escalated THEN 1 ELSE 0 END)::DOUBLE
                / NULLIF(COUNT(*), 0) AS escalation_rate
            FROM tickets
            WHERE reporting_eligible_flag = TRUE
              AND csat_available_flag = TRUE
            GROUP BY service_area
            HAVING COUNT(*) >= 50
            ORDER BY ticket_count DESC, average_csat ASC
            LIMIT 10
            """
            return SQLCandidate(
                sql=sql,
                purpose="Identify service areas with high ticket volume and low CSAT.",
                tables_used=["tickets"],
                columns_used=[
                    "service_area",
                    "csat_score",
                    "is_escalated",
                    "reporting_eligible_flag",
                    "csat_available_flag",
                ],
                metrics_used=["total_tickets", "average_csat", "escalation_rate"],
                expected_columns=[
                    "service_area",
                    "ticket_count",
                    "average_csat",
                    "escalation_rate",
                ],
                detail_query=False,
                max_rows=10,
            )
        if "priority" in plan.dimensions:
            filtered_priority = any("priority IN" in item for item in plan.filters)
            if filtered_priority:
                sql = """
                SELECT
                  priority,
                  COUNT(*) AS ticket_count,
                  MEDIAN(resolution_time_hours) AS median_resolution_hours,
                  1.0 - (
                    SUM(CASE WHEN calculated_sla_breached THEN 1 ELSE 0 END)::DOUBLE
                    / NULLIF(COUNT(*), 0)
                  ) AS sla_compliance_rate
                FROM tickets
                WHERE reporting_eligible_flag = TRUE
                  AND priority IN ('Urgent', 'Low')
                  AND is_closed_ticket = TRUE
                  AND valid_resolved_date_flag = TRUE
                  AND resolution_time_hours IS NOT NULL
                GROUP BY priority
                ORDER BY median_resolution_hours DESC, priority
                """
            else:
                sql = """
            SELECT
              priority,
              COUNT(*) AS ticket_count,
              MEDIAN(resolution_time_hours) AS median_resolution_hours,
              1.0 - (
                SUM(CASE WHEN calculated_sla_breached THEN 1 ELSE 0 END)::DOUBLE
                / NULLIF(COUNT(*), 0)
              ) AS sla_compliance_rate
            FROM tickets
            WHERE reporting_eligible_flag = TRUE
              AND is_closed_ticket = TRUE
              AND valid_resolved_date_flag = TRUE
              AND resolution_time_hours IS NOT NULL
            GROUP BY priority
            ORDER BY median_resolution_hours DESC, priority
            """
            purpose = (
                "Compare SLA compliance and median resolution time for urgent and "
                "low-priority tickets."
                if filtered_priority
                else "Compare ticket resolution performance by priority."
            )
            return SQLCandidate(
                sql=sql,
                purpose=purpose,
                tables_used=["tickets"],
                columns_used=[
                    "priority",
                    "resolution_time_hours",
                    "calculated_sla_breached",
                    "reporting_eligible_flag",
                    "is_closed_ticket",
                    "valid_resolved_date_flag",
                ],
                metrics_used=[
                    "sla_compliance_rate",
                    "total_tickets",
                    "median_resolution_hours",
                ],
                expected_columns=[
                    "priority",
                    "ticket_count",
                    "median_resolution_hours",
                    "sla_compliance_rate",
                ],
                detail_query=False,
                max_rows=10,
            )
        if "team" in plan.dimensions:
            sql = """
            SELECT
              team,
              COUNT(*) AS ticket_count,
              1.0 - (
                SUM(CASE WHEN calculated_sla_breached THEN 1 ELSE 0 END)::DOUBLE
                / NULLIF(COUNT(*), 0)
              ) AS sla_compliance_rate,
              MEDIAN(resolution_time_hours) AS median_resolution_hours
            FROM tickets
            WHERE reporting_eligible_flag = TRUE
              AND created_year = 2024
              AND is_closed_ticket = TRUE
              AND valid_resolved_date_flag = TRUE
              AND resolution_time_hours IS NOT NULL
            GROUP BY team
            ORDER BY sla_compliance_rate ASC, ticket_count DESC
            LIMIT 10
            """
            return SQLCandidate(
                sql=sql,
                purpose="Rank teams by SLA compliance in 2024.",
                tables_used=["tickets"],
                columns_used=[
                    "team",
                    "calculated_sla_breached",
                    "resolution_time_hours",
                    "reporting_eligible_flag",
                    "created_year",
                    "is_closed_ticket",
                    "valid_resolved_date_flag",
                ],
                metrics_used=["sla_compliance_rate", "total_tickets", "median_resolution_hours"],
                expected_columns=[
                    "team",
                    "ticket_count",
                    "sla_compliance_rate",
                    "median_resolution_hours",
                ],
                detail_query=False,
                max_rows=10,
            )
        sql = """
        SELECT
          reporting_category,
          reporting_subcategory,
          COUNT(*) AS ticket_count,
          1.0 - (
            SUM(CASE WHEN calculated_sla_breached THEN 1 ELSE 0 END)::DOUBLE
            / NULLIF(COUNT(*), 0)
          ) AS sla_compliance_rate,
          MEDIAN(resolution_time_hours) AS median_resolution_hours,
          AVG(csat_score) AS average_csat
        FROM tickets
        WHERE reporting_eligible_flag = TRUE
          AND is_closed_ticket = TRUE
          AND valid_resolved_date_flag = TRUE
          AND resolution_time_hours IS NOT NULL
        GROUP BY reporting_category, reporting_subcategory
        ORDER BY sla_compliance_rate ASC, ticket_count DESC
        LIMIT 10
        """
        return SQLCandidate(
            sql=sql,
            purpose="Rank issue categories by volume, SLA compliance, resolution time, and CSAT.",
            tables_used=["tickets"],
            columns_used=[
                "reporting_category",
                "reporting_subcategory",
                "calculated_sla_breached",
                "resolution_time_hours",
                "csat_score",
                "reporting_eligible_flag",
                "is_closed_ticket",
                "valid_resolved_date_flag",
            ],
            metrics_used=[
                "total_tickets",
                "sla_compliance_rate",
                "median_resolution_hours",
                "average_csat",
            ],
            expected_columns=[
                "reporting_category",
                "reporting_subcategory",
                "ticket_count",
                "sla_compliance_rate",
                "median_resolution_hours",
                "average_csat",
            ],
            detail_query=False,
            max_rows=10,
        )
