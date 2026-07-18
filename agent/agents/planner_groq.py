"""Groq-backed planner role."""

from __future__ import annotations

import json
from typing import Any

from agent.llm.base import StructuredLLMClient
from agent.llm.models import StructuredCompletion
from agent.llm.prompts import load_prompt
from agent.models import AnalysisPlan
from agent.settings import Settings, get_settings
from agent.tools.config_loader import load_yaml
from agent.tools.metric_tool import get_metric_definitions
from agent.tools.schema_tool import get_dataset_schema


def _json_default(value: Any) -> str:
    return str(value)


class GroqPlannerAgent:
    def __init__(self, client: StructuredLLMClient, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.prompt, self.prompt_version = load_prompt("planner", self.settings)

    def plan(self, question: str) -> StructuredCompletion[AnalysisPlan]:
        payload = {
            "question": question,
            "approved_schema": get_dataset_schema(self.settings),
            "approved_metrics": get_metric_definitions(settings=self.settings),
            "policy": load_yaml(self.settings.config_dir / "policy.yaml"),
            "default_scope": "Use 2024-2025 reporting-eligible tickets unless requested otherwise.",
            "response_schema": AnalysisPlan.model_json_schema(),
        }
        return self.client.complete_model(
            system_prompt=self.prompt,
            user_prompt=json.dumps(payload, default=_json_default),
            response_model=AnalysisPlan,
            max_tokens=self.settings.max_completion_tokens,
            reasoning_effort="medium",
            temperature=self.settings.temperature,
            role="planner",
            prompt_version=self.prompt_version,
        )
