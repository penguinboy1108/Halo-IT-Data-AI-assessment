"""Groq-backed SQL producer role."""

from __future__ import annotations

import json
from typing import Any

from agent.llm.base import StructuredLLMClient
from agent.llm.models import StructuredCompletion
from agent.llm.prompts import load_prompt
from agent.models import AnalysisPlan, SQLCandidate
from agent.settings import Settings, get_settings
from agent.tools.config_loader import load_yaml
from agent.tools.metric_tool import get_metric_definitions
from agent.tools.schema_tool import get_dataset_schema


def _json_default(value: Any) -> str:
    return str(value)


class GroqSQLProducerAgent:
    def __init__(self, client: StructuredLLMClient, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.prompt, self.prompt_version = load_prompt("sql_producer", self.settings)

    def produce(
        self, plan: AnalysisPlan, feedback: str | None = None
    ) -> StructuredCompletion[SQLCandidate]:
        metric_names = plan.metrics or None
        payload = {
            "approved_plan": plan.model_dump(),
            "approved_schema": get_dataset_schema(self.settings),
            "metric_definitions": get_metric_definitions(metric_names, self.settings),
            "sql_policy": load_yaml(self.settings.config_dir / "policy.yaml")["sql"],
            "retry_feedback": feedback,
            "response_schema": SQLCandidate.model_json_schema(),
        }
        return self.client.complete_model(
            system_prompt=self.prompt,
            user_prompt=json.dumps(payload, default=_json_default),
            response_model=SQLCandidate,
            max_tokens=self.settings.max_completion_tokens,
            reasoning_effort="medium",
            temperature=self.settings.temperature,
            role="sql_producer",
            prompt_version=self.prompt_version,
        )
