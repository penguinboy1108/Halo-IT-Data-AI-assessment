"""Orchestration for the analytics agent."""

from __future__ import annotations

import re
from time import perf_counter
from typing import Any, cast
from uuid import uuid4

from pydantic import BaseModel

from agent.agents.evaluator import EvaluatorAgent
from agent.agents.evaluator_groq import GroqEvaluatorAgent
from agent.agents.insight_producer import InsightProducerAgent
from agent.agents.insight_producer_groq import GroqInsightProducerAgent
from agent.agents.planner import PlannerAgent
from agent.agents.planner_groq import GroqPlannerAgent
from agent.agents.sql_producer import SQLProducerAgent
from agent.agents.sql_producer_groq import GroqSQLProducerAgent
from agent.audit_log import AuditLogger
from agent.llm.base import StructuredLLMClient
from agent.llm.groq_client import GroqJSONClient
from agent.llm.models import StructuredCompletion
from agent.llm.prompts import prompt_versions
from agent.llm.token_accounting import (
    combine_usage,
    usage_from_text,
    value_per_1k_tokens,
    value_per_usd,
    value_score,
)
from agent.models import (
    AgentResponse,
    AgentTrace,
    AnalysisPlan,
    EvaluationResult,
    FinalAnswerDraft,
    QueryResult,
    SQLCandidate,
    UsageRecord,
)
from agent.settings import Settings, get_settings
from agent.state import AgentState
from agent.tools.duckdb_tool import run_read_only_query
from agent.tools.quality_tool import get_data_quality_context
from agent.tools.sql_guard import validate_sql


def _elapsed_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


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
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm_client: StructuredLLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.guard = InputGuard(self.settings)
        self.audit_logger = AuditLogger(self.settings)
        self.use_groq = not self.settings.use_fake_llm
        self.llm_client = llm_client
        self.planner: Any
        self.sql_producer: Any
        self.insight_producer: Any
        self.evaluator: Any

        if self.use_groq:
            client = self.llm_client or GroqJSONClient(self.settings)
            self.planner = GroqPlannerAgent(client, self.settings)
            self.sql_producer = GroqSQLProducerAgent(client, self.settings)
            self.insight_producer = GroqInsightProducerAgent(client, self.settings)
            self.evaluator = GroqEvaluatorAgent(client, self.settings)
        else:
            self.planner = PlannerAgent(self.settings)
            self.sql_producer = SQLProducerAgent(self.settings)
            self.insight_producer = InsightProducerAgent()
            self.evaluator = EvaluatorAgent()

    def answer(self, question: str) -> AgentResponse:
        request_id = f"req_{uuid4().hex[:12]}"
        trace_id = f"trc_{uuid4().hex[:12]}"
        started = perf_counter()
        trace = self._new_trace()
        generated_sql: str | None = None
        validated_sql: str | None = None
        validation_risk_flags: list[str] = []

        refusal = self.guard.refusal_reason(question)
        if refusal:
            response = self._finalise_response(
                AgentResponse(state=AgentState.REFUSED, refusal_reason=refusal, trace=trace)
            )
            self._log(
                request_id,
                trace_id,
                question,
                response,
                started,
            )
            return response

        plan_started = perf_counter()
        plan = self._plan(question, trace)
        trace.latency_ms_by_stage["planner"] = _elapsed_ms(plan_started)
        if plan.clarification_needed:
            response = self._finalise_response(
                AgentResponse(
                    state=AgentState.REFUSED,
                    plan=plan,
                    refusal_reason=plan.clarification_question
                    or "Please clarify the requested analysis.",
                    trace=trace,
                )
            )
            self._log(request_id, trace_id, question, response, started)
            return response
        if not plan.answerable:
            response = self._finalise_response(
                AgentResponse(
                    state=AgentState.REFUSED,
                    plan=plan,
                    refusal_reason=plan.refusal_reason,
                    trace=trace,
                )
            )
            self._log(request_id, trace_id, question, response, started)
            return response

        caveats = [
            row.get("notes", "")
            for row in get_data_quality_context(plan.caveat_topics, self.settings)[:3]
            if row.get("notes")
        ]
        feedback: str | None = None
        attempt = 0
        while attempt <= self.settings.max_retries:
            trace.retry_count = attempt
            sql_started = perf_counter()
            candidate = self._produce_sql(plan, feedback, trace)
            trace.latency_ms_by_stage["sql_producer"] = trace.latency_ms_by_stage.get(
                "sql_producer", 0
            ) + _elapsed_ms(sql_started)
            generated_sql = candidate.sql

            validation_started = perf_counter()
            validation = validate_sql(
                candidate.sql, detail_query=candidate.detail_query, settings=self.settings
            )
            trace.latency_ms_by_stage["sql_validation"] = trace.latency_ms_by_stage.get(
                "sql_validation", 0
            ) + _elapsed_ms(validation_started)
            validated_sql = validation.normalised_sql
            validation_risk_flags = validation.risk_flags
            trace.validation_flags = validation.risk_flags
            if not validation.approved or not validation.normalised_sql:
                if attempt >= self.settings.max_retries:
                    response = self._finalise_response(
                        AgentResponse(
                            state=AgentState.FAILED,
                            plan=plan,
                            sql=candidate.sql,
                            refusal_reason=validation.reason or "SQL failed validation.",
                            trace=trace,
                        )
                    )
                    self._log(
                        request_id,
                        trace_id,
                        question,
                        response,
                        started,
                        generated_sql=generated_sql,
                        validated_sql=validated_sql,
                        validation_risk_flags=validation_risk_flags,
                    )
                    return response
                feedback = validation.reason or "SQL failed local validation."
                attempt += 1
                continue

            query_started = perf_counter()
            result = run_read_only_query(
                validation.normalised_sql,
                candidate.purpose,
                max_rows=candidate.max_rows,
                settings=self.settings,
            )
            trace.latency_ms_by_stage["duckdb_query"] = trace.latency_ms_by_stage.get(
                "duckdb_query", 0
            ) + _elapsed_ms(query_started)
            trace.result_row_count = result.row_count
            trace.result_cell_count = result.row_count * len(result.columns)

            answer_started = perf_counter()
            answer = self._draft_answer(question, plan, result, caveats, trace)
            answer = self._normalise_answer_provenance(answer, plan, result)
            trace.latency_ms_by_stage["insight_producer"] = trace.latency_ms_by_stage.get(
                "insight_producer", 0
            ) + _elapsed_ms(answer_started)

            eval_started = perf_counter()
            evaluation = self._evaluate(
                question,
                plan,
                validation.normalised_sql,
                result,
                answer,
                caveats,
                trace,
            )
            trace.latency_ms_by_stage["evaluator"] = trace.latency_ms_by_stage.get(
                "evaluator", 0
            ) + _elapsed_ms(eval_started)

            if not evaluation.hard_fail:
                response = self._finalise_response(
                    AgentResponse(
                        state=AgentState.COMPLETED,
                        answer=answer,
                        evaluation=evaluation,
                        plan=plan,
                        query_result=result,
                        sql=validation.normalised_sql,
                        trace=trace,
                    )
                )
                self._log(
                    request_id,
                    trace_id,
                    question,
                    response,
                    started,
                    generated_sql=generated_sql,
                    validated_sql=validated_sql,
                    validation_risk_flags=validation_risk_flags,
                )
                return response

            if not evaluation.retry_required or attempt >= self.settings.max_retries:
                response = self._finalise_response(
                    AgentResponse(
                        state=AgentState.FAILED,
                        answer=answer,
                        evaluation=evaluation,
                        plan=plan,
                        query_result=result,
                        sql=validation.normalised_sql,
                        refusal_reason="Evaluator hard-failed the answer.",
                        trace=trace,
                    )
                )
                self._log(
                    request_id,
                    trace_id,
                    question,
                    response,
                    started,
                    generated_sql=generated_sql,
                    validated_sql=validated_sql,
                    validation_risk_flags=validation_risk_flags,
                )
                return response

            feedback = evaluation.suggested_revision or "Evaluator requested revision."
            attempt += 1

        response = self._finalise_response(
            AgentResponse(
                state=AgentState.FAILED,
                plan=plan,
                refusal_reason="Retry budget exhausted.",
                trace=trace,
            )
        )
        self._log(request_id, trace_id, question, response, started)
        return response

    def _new_trace(self) -> AgentTrace:
        trace = AgentTrace(
            planner_type="groq" if self.use_groq else "deterministic",
            sql_producer_type="groq" if self.use_groq else "deterministic",
            insight_producer_type="groq" if self.use_groq else "deterministic",
            evaluator_type="groq" if self.use_groq else "deterministic",
            prompt_versions=prompt_versions(self.settings),
        )
        return trace

    def _record_completion(
        self, completion: StructuredCompletion[BaseModel], trace: AgentTrace
    ) -> None:
        previous = trace.token_usage_by_role.get(completion.role)
        trace.token_usage_by_role[completion.role] = (
            combine_usage(previous, completion.usage) if previous else completion.usage
        )
        trace.prompt_versions[completion.role] = completion.prompt_version

    def _record_estimated_usage(
        self,
        *,
        role: str,
        prompt: str,
        completion: str,
        trace: AgentTrace,
    ) -> None:
        usage = usage_from_text(prompt, completion)
        previous = trace.token_usage_by_role.get(role)
        trace.token_usage_by_role[role] = combine_usage(previous, usage) if previous else usage

    def _plan(self, question: str, trace: AgentTrace) -> AnalysisPlan:
        if self.use_groq:
            completion = self.planner.plan(question)
            self._record_completion(completion, trace)
            return cast(AnalysisPlan, completion.value)
        plan = self.planner.plan(question)
        self._record_estimated_usage(
            role="planner",
            prompt=question,
            completion=plan.model_dump_json(),
            trace=trace,
        )
        return cast(AnalysisPlan, plan)

    def _produce_sql(
        self, plan: AnalysisPlan, feedback: str | None, trace: AgentTrace
    ) -> SQLCandidate:
        if self.use_groq:
            completion = self.sql_producer.produce(plan, feedback=feedback)
            self._record_completion(completion, trace)
            return cast(SQLCandidate, completion.value)
        candidate = self.sql_producer.produce(plan, feedback=feedback)
        self._record_estimated_usage(
            role="sql_producer",
            prompt=plan.model_dump_json() + (feedback or ""),
            completion=candidate.sql,
            trace=trace,
        )
        return cast(SQLCandidate, candidate)

    def _draft_answer(
        self,
        question: str,
        plan: AnalysisPlan,
        result: QueryResult,
        caveats: list[str],
        trace: AgentTrace,
    ) -> FinalAnswerDraft:
        if self.use_groq:
            completion = self.insight_producer.draft(question, plan, result, caveats)
            self._record_completion(completion, trace)
            return cast(FinalAnswerDraft, completion.value)
        answer = self.insight_producer.draft(question, plan, result, caveats)
        self._record_estimated_usage(
            role="insight_producer",
            prompt=question + plan.model_dump_json() + result.model_dump_json(),
            completion=answer.answer_markdown,
            trace=trace,
        )
        return cast(FinalAnswerDraft, answer)

    def _normalise_answer_provenance(
        self, answer: FinalAnswerDraft, plan: AnalysisPlan, result: QueryResult
    ) -> FinalAnswerDraft:
        filters = answer.filters_applied or plan.filters
        return answer.model_copy(
            update={
                "filters_applied": filters,
                "rows_analysed": result.source_row_count,
                "query_id": result.query_id,
                "dataset_version": result.dataset_version,
            }
        )

    def _evaluate(
        self,
        question: str,
        plan: AnalysisPlan,
        sql: str,
        result: QueryResult,
        answer: FinalAnswerDraft,
        caveats: list[str],
        trace: AgentTrace,
    ) -> EvaluationResult:
        if self.use_groq:
            completion = self.evaluator.evaluate(
                question=question,
                plan=plan,
                sql=sql,
                result=result,
                answer=answer,
                caveats=caveats,
            )
            self._record_completion(completion, trace)
            return cast(EvaluationResult, completion.value)
        evaluation = self.evaluator.evaluate(
            answer,
            question=question,
            plan=plan,
            sql=sql,
            result=result,
            caveats=caveats,
        )
        self._record_estimated_usage(
            role="evaluator",
            prompt=question + sql + answer.answer_markdown,
            completion=evaluation.model_dump_json(),
            trace=trace,
        )
        return cast(EvaluationResult, evaluation)

    def _finalise_response(self, response: AgentResponse) -> AgentResponse:
        usage_records = list(response.trace.token_usage_by_role.values())
        response.usage = combine_usage(*usage_records) if usage_records else UsageRecord()
        if response.evaluation:
            score = value_score(
                response.evaluation,
                task_completion=0.0 if response.evaluation.hard_fail else 1.0,
            )
        else:
            score = 0.0
        response.value_per_1k_tokens = value_per_1k_tokens(score, response.usage.total_tokens)
        response.value_per_usd = value_per_usd(score, response.usage.estimated_cost_usd)
        return response

    def _log(
        self,
        request_id: str,
        trace_id: str,
        question: str,
        response: AgentResponse,
        started: float,
        *,
        generated_sql: str | None = None,
        validated_sql: str | None = None,
        validation_risk_flags: list[str] | None = None,
    ) -> None:
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
