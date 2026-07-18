"""Structured JSONL audit logging for every agent request."""

from __future__ import annotations

import hashlib
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from agent.models import AgentResponse
from agent.settings import Settings, get_settings

_LOCK = threading.Lock()
_RENDERER = structlog.processors.JSONRenderer(sort_keys=True)

SECRET_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(GROQ_API_KEY|OPENAI_API_KEY)\s*=\s*[^\s]+"),
]
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def redact_text(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)


def question_hash(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


class AuditLogger:
    """Append-only request audit logger.

    The log intentionally stores redacted user text plus a stable hash. SQL is
    logged in full because it is generated from approved schema and is essential
    for assessment auditability.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.path = Path(self.settings.audit_log_path)

    def log_request(
        self,
        *,
        request_id: str,
        trace_id: str,
        question: str,
        response: AgentResponse,
        latency_ms: float,
        generated_sql: str | None = None,
        validated_sql: str | None = None,
        validation_risk_flags: list[str] | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "event": "agent_request",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "trace_id": trace_id,
            "state": str(response.state),
            "agent_mode": "fake" if self.settings.use_fake_llm else "groq",
            "model": self.settings.groq_model,
            "question_hash": question_hash(question),
            "question_redacted": redact_text(question)[:500],
            "refusal_reason": response.refusal_reason,
            "generated_sql": generated_sql,
            "validated_sql": validated_sql,
            "validation_risk_flags": validation_risk_flags or [],
            "planner_type": response.trace.planner_type,
            "sql_producer_type": response.trace.sql_producer_type,
            "insight_producer_type": response.trace.insight_producer_type,
            "evaluator_type": response.trace.evaluator_type,
            "prompt_versions": response.trace.prompt_versions,
            "retry_count": response.trace.retry_count,
            "token_usage_by_role": {
                role: usage.model_dump()
                for role, usage in response.trace.token_usage_by_role.items()
            },
            "latency_ms_by_stage": response.trace.latency_ms_by_stage,
            "result_row_count": response.trace.result_row_count,
            "result_cell_count": response.trace.result_cell_count,
            "query_id": response.answer.query_id if response.answer else None,
            "dataset_version": response.answer.dataset_version if response.answer else None,
            "rows_analysed": response.answer.rows_analysed if response.answer else None,
            "confidence": response.answer.confidence if response.answer else None,
            "filters_applied": response.answer.filters_applied if response.answer else [],
            "quality_score": response.evaluation.quality_score if response.evaluation else None,
            "evaluation_hard_fail": response.evaluation.hard_fail if response.evaluation else None,
            "evaluation_issues": response.evaluation.issues if response.evaluation else [],
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "estimated_cost_usd": response.usage.estimated_cost_usd,
            "usage_source": response.usage.source,
            "value_per_1k_tokens": response.value_per_1k_tokens,
            "value_per_usd": response.value_per_usd,
            "latency_ms": round(latency_ms, 2),
        }
        self._append(event)

    def _append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = str(_RENDERER(None, "agent_request", event))
        with _LOCK, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
