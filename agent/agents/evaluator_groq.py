"""Groq-backed independent evaluator role."""

from __future__ import annotations

import json
from typing import Any

from agent.llm.base import StructuredLLMClient
from agent.llm.models import StructuredCompletion
from agent.llm.prompts import load_prompt
from agent.models import AnalysisPlan, EvaluationResult, FinalAnswerDraft, QueryResult
from agent.settings import Settings, get_settings
from agent.tools.result_summary import summarise_query_result


def _json_default(value: Any) -> str:
    return str(value)


class GroqEvaluatorAgent:
    def __init__(self, client: StructuredLLMClient, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.prompt, self.prompt_version = load_prompt("evaluator", self.settings)

    def evaluate(
        self,
        *,
        question: str,
        plan: AnalysisPlan,
        sql: str,
        result: QueryResult,
        answer: FinalAnswerDraft,
        caveats: list[str],
    ) -> StructuredCompletion[EvaluationResult]:
        payload = {
            "question": question,
            "approved_plan": plan.model_dump(),
            "validated_sql": sql,
            "verified_query_result": summarise_query_result(result),
            "draft_answer": answer.model_dump(),
            "data_quality_caveats": caveats,
            "response_schema": EvaluationResult.model_json_schema(),
        }
        return self.client.complete_model(
            system_prompt=self.prompt,
            user_prompt=json.dumps(payload, default=_json_default),
            response_model=EvaluationResult,
            max_tokens=self.settings.max_completion_tokens,
            reasoning_effort="medium",
            temperature=self.settings.temperature,
            role="evaluator",
            prompt_version=self.prompt_version,
        )
