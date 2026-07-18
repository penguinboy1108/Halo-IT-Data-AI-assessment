from agent.llm.token_accounting import (
    combine_usage,
    estimate_cost_usd,
    usage_from_provider,
    value_per_1k_tokens,
    value_per_usd,
)


def test_estimate_cost_usd():
    assert estimate_cost_usd(1_000_000, 1_000_000) == 0.9


def test_value_per_1k_tokens():
    assert value_per_1k_tokens(0.5, 500) == 1.0


def test_value_per_usd_floor():
    assert value_per_usd(0.5, 0) == 500000


def test_provider_usage_and_combination():
    first = usage_from_provider(prompt_tokens=10, completion_tokens=5)
    second = usage_from_provider(prompt_tokens=20, completion_tokens=10)
    combined = combine_usage(first, second)

    assert combined.prompt_tokens == 30
    assert combined.completion_tokens == 15
    assert combined.total_tokens == 45
    assert combined.source == "provider"
