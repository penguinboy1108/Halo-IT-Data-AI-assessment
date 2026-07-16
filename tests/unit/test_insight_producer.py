from agent.agents.insight_producer import InsightProducerAgent
from agent.models import AnalysisPlan, QueryResult


def test_insight_producer_adds_business_analysis_sections():
    plan = AnalysisPlan(
        answerable=True,
        intent="comparison",
        metrics=["sla_compliance_rate", "total_tickets"],
        dimensions=["team"],
        filters=["reporting_eligible_flag = TRUE", "created_year = 2024"],
        sort=["sla_compliance_rate ASC"],
        expected_output="Rank teams by SLA compliance in 2024.",
    )
    result = QueryResult(
        query_id="qry_test",
        columns=["team", "ticket_count", "sla_compliance_rate", "median_resolution_hours"],
        rows=[
            {
                "team": "Platform Support",
                "ticket_count": 1200,
                "sla_compliance_rate": 0.68,
                "median_resolution_hours": 31.5,
            }
        ],
        row_count=1,
        source_row_count=67136,
        execution_ms=12,
        truncated=False,
        dataset_version="test",
        sql_hash="abc123",
    )

    answer = InsightProducerAgent().draft("Which team had the lowest SLA?", plan, result, [])

    assert "Business interpretation" in answer.answer_markdown
    assert "Possible drivers to investigate" in answer.answer_markdown
    assert "Recommended actions" in answer.answer_markdown
    assert "Platform Support" in answer.answer_markdown
    assert "68.0%" in answer.answer_markdown
