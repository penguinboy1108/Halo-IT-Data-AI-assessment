from agent.llm.fake_client import FakeStructuredLLMClient
from agent.models import AnalysisPlan, EvaluationResult, FinalAnswerDraft, SQLCandidate
from agent.orchestrator import AnalyticsOrchestrator
from agent.settings import Settings
from agent.state import AgentState
from scripts.build_duckdb import build_database


def _plan() -> AnalysisPlan:
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
        limit=5,
        caveat_topics=["sla", "team_mix"],
        expected_output="Rank teams by SLA compliance in 2024.",
    )


def _safe_team_sql() -> SQLCandidate:
    return SQLCandidate(
        sql="""
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
        LIMIT 5
        """,
        purpose="Rank teams by SLA compliance.",
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
        max_rows=5,
    )


def _answer() -> FinalAnswerDraft:
    return FinalAnswerDraft(
        finding="Provisioning is the weakest SLA signal.",
        evidence=[],
        operational_interpretation="Treat this as a queue signal, not employee scoring.",
        recommended_action="Review case mix and hand-offs.",
        caveats=["SLA uses calculated_sla_breached."],
        filters_applied=[],
        rows_analysed=0,
        query_id="model_placeholder",
        dataset_version="model_placeholder",
        confidence="high",
        answer_markdown="**Finding**\nProvisioning is the weakest SLA signal.",
    )


def _evaluation(*, hard_fail: bool = False) -> EvaluationResult:
    score = 0.0 if hard_fail else 0.92
    return EvaluationResult(
        correctness=score,
        groundedness=score,
        completeness=0.9 if not hard_fail else 0.0,
        relevance=0.9 if not hard_fail else 0.0,
        safety=1.0 if not hard_fail else 0.0,
        caveat_quality=0.9 if not hard_fail else 0.0,
        actionability=0.9 if not hard_fail else 0.0,
        cost_efficiency=0.95,
        hard_fail=hard_fail,
        issues=["bad SQL"] if hard_fail else [],
        suggested_revision="Regenerate with approved columns." if hard_fail else None,
        retry_required=hard_fail,
    )


def test_orchestrator_uses_mocked_groq_stack(tmp_path):
    db_path = tmp_path / "halo_test.duckdb"
    build_database(db_path=db_path)
    settings = Settings(AGENT_LLM_MODE="groq", GROQ_API_KEY="gsk_test")
    settings.db_path = db_path
    client = FakeStructuredLLMClient([_plan(), _safe_team_sql(), _answer(), _evaluation()])

    response = AnalyticsOrchestrator(settings, llm_client=client).answer(
        "Which team had the lowest SLA compliance in 2024?"
    )

    assert response.state == AgentState.COMPLETED
    assert response.trace.planner_type == "groq"
    assert response.trace.token_usage_by_role["planner"].total_tokens > 0
    assert response.answer is not None
    assert response.query_result is not None
    assert response.answer.query_id == response.query_result.query_id


def test_orchestrator_retries_after_sql_validation_failure(tmp_path):
    db_path = tmp_path / "halo_test.duckdb"
    build_database(db_path=db_path)
    settings = Settings(AGENT_LLM_MODE="groq", GROQ_API_KEY="gsk_test")
    settings.db_path = db_path
    settings.max_retries = 1
    bad_sql = SQLCandidate(
        sql="SELECT * FROM tickets LIMIT 5",
        purpose="Invalid wildcard query.",
        tables_used=["tickets"],
        columns_used=[],
        metrics_used=[],
        expected_columns=[],
        detail_query=False,
        max_rows=5,
    )
    client = FakeStructuredLLMClient([_plan(), bad_sql, _safe_team_sql(), _answer(), _evaluation()])

    response = AnalyticsOrchestrator(settings, llm_client=client).answer(
        "Which team had the lowest SLA compliance in 2024?"
    )

    assert response.state == AgentState.COMPLETED
    assert response.trace.retry_count == 1
    assert response.sql is not None
    assert "SELECT *" not in response.sql
