"""Structured LLM provider interface."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from agent.llm.models import StructuredCompletion

T = TypeVar("T", bound=BaseModel)


class StructuredLLMClient(Protocol):
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
        """Return a Pydantic-validated structured completion."""
