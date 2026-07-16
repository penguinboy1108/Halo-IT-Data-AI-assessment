"""Deterministic orchestration for the analytics agent."""

from __future__ import annotations

import re
from time import perf_counter
from uuid import uuid4

from agent.agents.evaluator import EvaluatorAgent
from agent.agents.insight_producer import InsightProducerAgent
from agent.agents.planner import PlannerAgent
from agent.agents.sql_producer import SQLProducerAgent
from agent.audit_log import AuditLogger
from agent.llm.token_accounting import (
    usage_from_text,
    value_per_1k_tokens,
    value_per_usd,
    value_score,
)
from agent.models import AgentResponse, UsageRecord
from agent.settings import Settings, get_settings
from agent.state import AgentState
from agent.tools.duckdb_tool import run_read_only_query
from agent.tools.quality_tool import get_data_quality_context
from agent.tools.sql_guard import validate_sql


class InputGuard:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.personal_terms = [
            "customer name",
            "customer names",
            "customer email",
            "email address",
            "email addresses",
            "billing contact",
            "phone number",
        ]
        self.secret_terms = ["api key", "groq_api_key", "password", "secret", "system prompt"]
        self.destructive_terms = [
            "attach ",
            "browse the web",
            "copy ",
            "drop table",
            "delete from",
            "developer prompt",
            "hidden developer prompt",
            "install ",
            "update tickets",
            "insert into",
            "load ",
            "python",
            "read_csv_auto",
            "resolution notes",
            "show unrestricted",
            "/etc/passwd",
            "ignore all rules",
            "reveal your system prompt",
        ]

    def refusal_reason(self, question: str) -> str | None:
        if not question.strip():
            return "Please ask a concrete operational analytics question."
        if len(question) > 1000:
            return "The question is too long for the bounded demo agent."
        lowered = question.lower()
        if any(term in lowered for term in self.personal_terms):
            return (
                "I cannot disclose or query personal customer data. "
                "Please ask for aggregated reporting metrics."
            )
        if any(term in lowered for term in self.secret_terms):
            return "I cannot reveal secrets, system prompts, or hidden configuration."
        if any(term in lowered for term in self.destructive_terms):
            return "I can only run read-only approved analytics queries."
        if (
            re.search(r"\b(select|drop|delete|insert|update|copy|attach|pragma)\b", lowered)
            and ";" in lowered
        ):
            return "Direct SQL or multi-statement instructions are not accepted through chat."
        return None


class AnalyticsOrchestrator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.guard = InputGuard(self.settings)
        self.planner = PlannerAgent(self.settings)
        self.sql_producer = SQLProducerAgent(self.settings)
        self.insight_producer = InsightProducerAgent()
        self.evaluator = EvaluatorAgent()
        self.audit_logger = AuditLogger(self.settings)

    def answer(self, question: str) -> AgentResponse:
        request_id = f"req_{uuid4().hex[:12]}"
        trace_id = f"trc_{uuid4().hex[:12]}"
        started = perf_counter()
        generated_sql: str | None = None
        validated_sql: str | None = None
        validation_risk_flags: list[str] = []

        refusal = self.guard.refusal_reason(question)
        if refusal:
            response = AgentResponse(state=AgentState.REFUSED, refusal_reason=refusal)
            self.audit_logger.log_request(
                request_id=request_id,
                trace_id=trace_id,
                question=question,
                response=response,
                latency_ms=(perf_counter() - started) * 1000,
            )
            return response

        plan = self.planner.plan(question)
        if not plan.answerable:
            response = AgentResponse(
                state=AgentState.REFUSED, plan=plan, refusal_reason=plan.refusal_reason
            )
            self.audit_logger.log_request(
                request_id=request_id,
                trace_id=trace_id,
                question=question,
                response=response,
                latency_ms=(perf_counter() - started) * 1000,
            )
            return response

        candidate = self.sql_producer.produce(plan)
        generated_sql = candidate.sql
        validation = validate_sql(
            candidate.sql, detail_query=candidate.detail_query, settings=self.settings
        )
        validated_sql = validation.normalised_sql
        validation_risk_flags = validation.risk_flags
        if not validation.approved or not validation.normalised_sql:
            response = AgentResponse(
                state=AgentState.FAILED,
                plan=plan,
                sql=candidate.sql,
                refusal_reason=validation.reason or "SQL failed validation.",
            )
            self.audit_logger.log_request(
                request_id=request_id,
                trace_id=trace_id,
                question=question,
                response=response,
                latency_ms=(perf_counter() - started) * 1000,
                generated_sql=generated_sql,
                validated_sql=validated_sql,
                validation_risk_flags=validation_risk_flags,
            )
            return response

        result = run_read_only_query(
            validation.normalised_sql,
            candidate.purpose,
            max_rows=candidate.max_rows,
            settings=self.settings,
        )
        quality_rows = get_data_quality_context(plan.caveat_topics, self.settings)
        caveats = [row.get("notes", "") for row in quality_rows[:3] if row.get("notes")]
        answer = self.insight_producer.draft(question, plan, result, caveats)
        evaluation = self.evaluator.evaluate(answer)

        usage = usage_from_text(question + candidate.sql, answer.answer_markdown)
        score = value_score(evaluation, task_completion=0.0 if evaluation.hard_fail else 1.0)
        response = AgentResponse(
            state=AgentState.COMPLETED if not evaluation.hard_fail else AgentState.FAILED,
            answer=answer,
            evaluation=evaluation,
            plan=plan,
            query_result=result,
            sql=validation.normalised_sql,
            usage=UsageRecord(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
            ),
            value_per_1k_tokens=value_per_1k_tokens(score, usage.total_tokens),
            value_per_usd=value_per_usd(score, usage.estimated_cost_usd),
        )
        self.audit_logger.log_request(
            request_id=request_id,
            trace_id=trace_id,
            question=question,
            response=response,
            latency_ms=(perf_counter() - started) * 1000,
            generated_sql=generated_sql,
            validated_sql=validated_sql,
            validation_risk_flags=validation_risk_flags,
        )
        return response
