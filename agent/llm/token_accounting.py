"""Token and value accounting."""

from __future__ import annotations

from typing import Literal

from agent.models import EvaluationResult, UsageRecord
from agent.settings import Settings, get_settings
from agent.tools.config_loader import load_yaml


def estimate_tokens(text: str) -> int:
    # Cheap deterministic approximation for local accounting.
    return max(1, int(len(text.split()) * 1.35))


def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    *,
    input_cost_per_1m_tokens: float = 0.15,
    output_cost_per_1m_tokens: float = 0.75,
) -> float:
    return (prompt_tokens / 1_000_000 * input_cost_per_1m_tokens) + (
        completion_tokens / 1_000_000 * output_cost_per_1m_tokens
    )


def usage_from_text(prompt: str, completion: str) -> UsageRecord:
    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = estimate_tokens(completion)
    return UsageRecord(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=estimate_cost_usd(prompt_tokens, completion_tokens),
        source="estimated",
    )


def model_pricing(
    *,
    provider: str = "groq",
    model: str | None = None,
    settings: Settings | None = None,
) -> tuple[float, float]:
    settings = settings or get_settings()
    model_name = model or settings.groq_model
    config = load_yaml(settings.config_dir / "models.yaml")
    model_config = config["providers"][provider]["models"][model_name]
    return (
        float(model_config["input_cost_per_1m_tokens"]),
        float(model_config["output_cost_per_1m_tokens"]),
    )


def usage_from_provider(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    provider: str = "groq",
    model: str | None = None,
    settings: Settings | None = None,
) -> UsageRecord:
    input_cost, output_cost = model_pricing(provider=provider, model=model, settings=settings)
    return UsageRecord(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=estimate_cost_usd(
            prompt_tokens,
            completion_tokens,
            input_cost_per_1m_tokens=input_cost,
            output_cost_per_1m_tokens=output_cost,
        ),
        source="provider",
    )


def combine_usage(*records: UsageRecord) -> UsageRecord:
    prompt_tokens = sum(record.prompt_tokens for record in records)
    completion_tokens = sum(record.completion_tokens for record in records)
    estimated_cost = sum(record.estimated_cost_usd for record in records)
    source: Literal["estimated", "provider"] = (
        "provider"
        if records and all(record.source == "provider" for record in records)
        else "estimated"
    )
    return UsageRecord(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=estimated_cost,
        source=source,
    )


def value_score(
    evaluation: EvaluationResult, *, task_completion: float = 1.0, user_feedback_factor: float = 1.0
) -> float:
    return evaluation.quality_score * task_completion * user_feedback_factor


def value_per_1k_tokens(value: float, total_tokens: int) -> float:
    return 1000 * value / max(total_tokens, 1)


def value_per_usd(value: float, estimated_cost_usd: float) -> float:
    return value / max(estimated_cost_usd, 0.000001)
