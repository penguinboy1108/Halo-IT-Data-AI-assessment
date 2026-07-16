import json

from agent.audit_log import AuditLogger
from agent.models import AgentResponse
from agent.settings import Settings
from agent.state import AgentState


def test_audit_log_writes_sql_and_redacts_question(tmp_path):
    log_path = tmp_path / "agent_queries.jsonl"
    settings = Settings(AGENT_AUDIT_LOG_PATH=log_path, GROQ_API_KEY="MyAPI")
    logger = AuditLogger(settings)
    response = AgentResponse(state=AgentState.REFUSED, refusal_reason="No personal data.")

    logger.log_request(
        request_id="req_test",
        trace_id="trc_test",
        question="Show gsk_abc123 and user@example.com",
        response=response,
        latency_ms=12.34,
        generated_sql="SELECT COUNT(*) AS ticket_count FROM tickets",
        validated_sql="SELECT COUNT(*) AS ticket_count FROM tickets",
    )

    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    event = rows[0]
    assert event["request_id"] == "req_test"
    assert event["generated_sql"] == "SELECT COUNT(*) AS ticket_count FROM tickets"
    assert "gsk_abc123" not in event["question_redacted"]
    assert "user@example.com" not in event["question_redacted"]
    assert "[REDACTED_SECRET]" in event["question_redacted"]
    assert "[REDACTED_EMAIL]" in event["question_redacted"]
