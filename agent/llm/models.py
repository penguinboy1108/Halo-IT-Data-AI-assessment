"""Shared LLM client contracts."""

from __future__ import annotations

from pydantic import BaseModel

from agent.models import UsageRecord


class StructuredCompletion[T: BaseModel](BaseModel):
    value: T
    usage: UsageRecord
    raw_model: str
    latency_ms: int
    role: str
    prompt_version: str
