"""Groq JSON client wrapper."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, TypeVar, cast

from groq import Groq
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from agent.exceptions import LLMError
from agent.llm.models import StructuredCompletion
from agent.llm.token_accounting import usage_from_provider
from agent.models import UsageRecord
from agent.settings import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class GroqJSONClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.groq_api_key or self.settings.groq_api_key == "MyAPI":
            raise LLMError("A real GROQ_API_KEY is required for Groq mode.")
        self.client = Groq(api_key=self.settings.groq_api_key)

    @retry(wait=wait_exponential_jitter(initial=1, max=8), stop=stop_after_attempt(3))
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.settings.temperature,
            max_completion_tokens=max_tokens or self.settings.max_completion_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Groq returned invalid JSON: {content[:200]}") from exc
        return cast(dict[str, Any], parsed)

    @retry(wait=wait_exponential_jitter(initial=1, max=8), stop=stop_after_attempt(3))
    def complete_model(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        max_tokens: int,
        reasoning_effort: str,
        temperature: float,
        role: str,
        prompt_version: str,
    ) -> StructuredCompletion[T]:
        del reasoning_effort
        started = perf_counter()
        response = self.client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        try:
            value = response_model.model_validate_json(content)
        except ValidationError as exc:
            raise LLMError(f"Groq returned invalid {response_model.__name__}: {exc}") from exc
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        if prompt_tokens or completion_tokens:
            usage_record: UsageRecord = usage_from_provider(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=self.settings.groq_model,
                settings=self.settings,
            )
        else:
            usage_record = UsageRecord()
        return StructuredCompletion(
            value=value,
            usage=usage_record,
            raw_model=self.settings.groq_model,
            latency_ms=int((perf_counter() - started) * 1000),
            role=role,
            prompt_version=prompt_version,
        )
