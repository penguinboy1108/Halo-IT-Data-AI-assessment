"""Planner role."""

from __future__ import annotations

from agent.models import AnalysisPlan
from agent.settings import Settings, get_settings


class PlannerAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def plan(self, question: str) -> AnalysisPlan:
        q = question.lower()
        if "data-quality" in q or "data quality" in q or "limitations" in q:
            return AnalysisPlan(
                answerable=True,
                intent="data_quality",
                metrics=["data_quality_summary"],
                dimensions=["metric"],
                filters=[],
                required_tools=["get_data_quality_context"],
                caveat_topics=["quality"],
                expected_output="Summarise the most material quality limitations.",
                complexity="low",
            )
        if "monthly" in q or "trend" in q or "change during 2024" in q:
            return AnalysisPlan(
                answerable=True,
                intent="trend",
                metrics=["total_tickets"],
                dimensions=["created_month", "created_month_name"],
                filters=["reporting_eligible_flag = TRUE", "created_year = 2024"],
                time_range="2024",
                sort=["created_month ASC"],
                expected_output="Monthly ticket volume trend for 2024.",
                complexity="low",
            )
        if "holiday" in q:
            return AnalysisPlan(
                answerable=True,
                intent="comparison",
                metrics=["total_tickets", "sla_compliance_rate", "median_first_response_hours"],
                dimensions=["holiday_period"],
                filters=["reporting_eligible_flag = TRUE"],
                caveat_topics=["holiday", "causality"],
                expected_output="Compare volume and service metrics by holiday period.",
                complexity="medium",
            )
        if "service area" in q or "service areas" in q:
            return AnalysisPlan(
                answerable=True,
                intent="diagnosis",
                metrics=["total_tickets", "average_csat"],
                dimensions=["service_area"],
                filters=["reporting_eligible_flag = TRUE", "csat_available_flag = TRUE"],
                sort=["ticket_count DESC", "average_csat ASC"],
                limit=10,
                expected_output="Find high-volume service areas with relatively low CSAT.",
                complexity="medium",
            )
        # Route explicit priority comparisons before generic resolution/category matching.
        if "urgent" in q and "low" in q:
            return AnalysisPlan(
                answerable=True,
                intent="comparison",
                metrics=["sla_compliance_rate", "total_tickets", "median_resolution_hours"],
                dimensions=["priority"],
                filters=[
                    "reporting_eligible_flag = TRUE",
                    "priority IN ('Urgent', 'Low')",
                    "is_closed_ticket = TRUE",
                    "valid_resolved_date_flag = TRUE",
                ],
                expected_output=(
                    "Compare SLA compliance and median resolution time for urgent and "
                    "low-priority tickets."
                ),
                complexity="low",
            )
        if "priority" in q or "priorities" in q:
            return AnalysisPlan(
                answerable=True,
                intent="comparison",
                metrics=["total_tickets", "median_resolution_hours", "sla_compliance_rate"],
                dimensions=["priority"],
                filters=[
                    "reporting_eligible_flag = TRUE",
                    "is_closed_ticket = TRUE",
                    "valid_resolved_date_flag = TRUE",
                ],
                sort=["median_resolution_hours DESC"],
                expected_output="Compare resolution time and SLA compliance by priority.",
                complexity="low",
            )
        # Route team/SLA questions before the generic category/resolution branch.
        if "team" in q or "teams" in q or "sla" in q:
            return AnalysisPlan(
                answerable=True,
                intent="comparison",
                metrics=["sla_compliance_rate", "total_tickets", "median_resolution_hours"],
                dimensions=["team"],
                filters=[
                    "reporting_eligible_flag = TRUE",
                    "created_year = 2024",
                    "is_closed_ticket = TRUE",
                    "valid_resolved_date_flag = TRUE",
                ],
                sort=["sla_compliance_rate ASC"],
                limit=10,
                caveat_topics=["sla", "team_mix"],
                expected_output="Rank teams by SLA compliance in 2024.",
                complexity="medium",
            )
        if "category" in q or "categories" in q or "resolution time" in q:
            return AnalysisPlan(
                answerable=True,
                intent="comparison",
                metrics=["total_tickets", "median_resolution_hours"],
                dimensions=["reporting_category", "reporting_subcategory"],
                filters=[
                    "reporting_eligible_flag = TRUE",
                    "is_closed_ticket = TRUE",
                    "valid_resolved_date_flag = TRUE",
                ],
                sort=["median_resolution_hours DESC"],
                limit=10,
                expected_output="Rank issue categories by median resolution time.",
                complexity="medium",
            )
        return AnalysisPlan(
            answerable=True,
            intent="diagnosis",
            metrics=["total_tickets", "sla_compliance_rate", "average_csat", "escalation_rate"],
            dimensions=["reporting_category"],
            filters=["reporting_eligible_flag = TRUE"],
            sort=["ticket_count DESC"],
            limit=10,
            caveat_topics=["diagnosis"],
            expected_output="Identify operational improvement focus areas.",
            complexity="medium",
        )
