"""Token and value accounting."""

from __future__ import annotations

from agent.models import EvaluationResult, UsageRecord


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
    )


def value_score(
    evaluation: EvaluationResult, *, task_completion: float = 1.0, user_feedback_factor: float = 1.0
) -> float:
    return evaluation.quality_score * task_completion * user_feedback_factor


def value_per_1k_tokens(value: float, total_tokens: int) -> float:
    return 1000 * value / max(total_tokens, 1)


def value_per_usd(value: float, estimated_cost_usd: float) -> float:
    return value / max(estimated_cost_usd, 0.000001)
