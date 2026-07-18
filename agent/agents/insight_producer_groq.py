"""Groq-backed insight producer role."""

from __future__ import annotations

import json
from typing import Any

from agent.llm.base import StructuredLLMClient
from agent.llm.models import StructuredCompletion
from agent.llm.prompts import load_prompt
from agent.models import AnalysisPlan, FinalAnswerDraft, QueryResult
from agent.settings import Settings, get_settings
from agent.tools.result_summary import summarise_query_result


def _json_default(value: Any) -> str:
    return str(value)


class GroqInsightProducerAgent:
    def __init__(self, client: StructuredLLMClient, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.prompt, self.prompt_version = load_prompt("insight_producer", self.settings)

    def draft(
        self,
        question: str,
        plan: AnalysisPlan,
        result: QueryResult,
        caveats: list[str],
    ) -> StructuredCompletion[FinalAnswerDraft]:
        payload = {
            "question": question,
            "approved_plan": plan.model_dump(),
            "verified_query_result": summarise_query_result(result),
            "query_provenance": {
                "query_id": result.query_id,
                "dataset_version": result.dataset_version,
                "rows_analysed": result.source_row_count,
                "result_rows": result.row_count,
                "sql_hash": result.sql_hash,
                "execution_ms": result.execution_ms,
            },
            "data_quality_caveats": caveats,
            "required_output": (
                "Return finding, evidence, operational_interpretation, recommended_action, "
                "caveats, filters_applied, rows_analysed, query_id, dataset_version, "
                "confidence, and answer_markdown."
            ),
            "response_schema": FinalAnswerDraft.model_json_schema(),
        }
        return self.client.complete_model(
            system_prompt=self.prompt,
            user_prompt=json.dumps(payload, default=_json_default),
            response_model=FinalAnswerDraft,
            max_tokens=self.settings.max_completion_tokens,
            reasoning_effort="medium",
            temperature=self.settings.temperature,
            role="insight_producer",
            prompt_version=self.prompt_version,
        )
