"""Deterministic structured LLM client for mocked integration tests."""

from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter
from typing import TypeVar

from pydantic import BaseModel

from agent.llm.models import StructuredCompletion
from agent.llm.token_accounting import usage_from_text
from agent.models import UsageRecord
from agent.settings import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class FakeStructuredLLMClient:
    """Queue-backed fake provider.

    The deterministic agent path does not need an LLM client. This class exists
    so Groq-mode orchestration can be tested without live provider calls.
    """

    def __init__(
        self,
        responses: Iterable[BaseModel],
        *,
        settings: Settings | None = None,
    ) -> None:
        self.responses = list(responses)
        self.settings = settings or get_settings()

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
        del max_tokens, reasoning_effort, temperature
        started = perf_counter()
        if not self.responses:
            raise AssertionError(f"No queued fake LLM response for role {role}.")
        value = self.responses.pop(0)
        if not isinstance(value, response_model):
            value = response_model.model_validate(value.model_dump())
        usage: UsageRecord = usage_from_text(
            system_prompt + "\n" + user_prompt, value.model_dump_json()
        )
        return StructuredCompletion(
            value=value,
            usage=usage,
            raw_model=self.settings.groq_model,
            latency_ms=int((perf_counter() - started) * 1000),
            role=role,
            prompt_version=prompt_version,
        )
