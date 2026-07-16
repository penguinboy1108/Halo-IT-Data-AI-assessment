"""Groq JSON client wrapper."""

from __future__ import annotations

import json
from typing import Any, cast

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from agent.exceptions import LLMError
from agent.settings import Settings, get_settings


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
