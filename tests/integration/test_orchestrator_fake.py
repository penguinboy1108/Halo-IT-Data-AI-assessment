from agent.orchestrator import AnalyticsOrchestrator
from agent.settings import Settings
from agent.state import AgentState
from scripts.build_duckdb import build_database


def test_orchestrator_answers_demo_question(tmp_path):
    db_path = tmp_path / "halo_test.duckdb"
    build_database(db_path=db_path)
    settings = Settings(
        AGENT_LLM_MODE="fake",
        AGENT_DB_PATH=db_path,
        AGENT_AUDIT_LOG_PATH=tmp_path / "agent_queries.jsonl",
    )

    orchestrator = AnalyticsOrchestrator(settings)
    response = orchestrator.answer("Which team had the lowest SLA compliance in 2024?")

    assert response.state == AgentState.COMPLETED
    assert response.answer is not None
    assert response.query_result is not None
    assert response.query_result.rows
    assert response.answer.query_id.startswith("qry_")
    assert "Finding" in response.answer.answer_markdown
