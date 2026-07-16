from agent.llm.token_accounting import estimate_cost_usd, value_per_1k_tokens, value_per_usd


def test_estimate_cost_usd():
    assert estimate_cost_usd(1_000_000, 1_000_000) == 0.9


def test_value_per_1k_tokens():
    assert value_per_1k_tokens(0.5, 500) == 1.0


def test_value_per_usd_floor():
    assert value_per_usd(0.5, 0) == 500000
