# Evaluation Methodology

The v1 evaluation suite is offline and deterministic. It verifies that normal demo questions complete and high-risk security questions are refused without requiring a live Groq key.

Suites:

- `smoke`: 51 business, quality, refusal, and safety cases.
- `security`: 12 refusal/security cases covering prompt injection, secret extraction, filesystem access, raw notes, destructive SQL, extension loading, external database attach, web access, and arbitrary Python requests.

Mocked Groq integration tests validate the live-mode orchestration path without calling Groq in CI. Those tests exercise Pydantic structured outputs, SQL validation, retry after invalid SQL, DuckDB execution, answer provenance normalisation, per-role usage, and trace metadata.

A limited owner-approved live Groq smoke test was completed successfully. Broader
live evaluation remains out of scope for this assessment because it would require
more formal third-party LLM data-egress approval and a larger benchmark plan.

Current v1 limitation: the runner verifies that refusal cases are refused and
normal cases complete, but it does not yet fully assert every configured
`expected_intent`, `expected_dimensions`, `required_metrics`, and
`required_filters`. Those fields are retained in the cases file to support a
future stricter evaluator.

Quality score:

```text
0.25 correctness
+ 0.20 groundedness
+ 0.15 completeness
+ 0.10 relevance
+ 0.10 safety
+ 0.08 caveat_quality
+ 0.07 actionability
+ 0.05 cost_efficiency
```

Value metrics:

```text
value_score = quality_score * task_completion * user_feedback_factor
value_per_1k_tokens = 1000 * value_score / max(total_tokens, 1)
value_per_usd = value_score / max(estimated_cost_usd, 0.000001)
```

Live model prompt changes should be proposed offline and manually reviewed before promotion.

CI and local validation should run:

```powershell
ruff check .
ruff format --check .
mypy agent
pytest --cov=agent --cov-report=term-missing
python -m agent.evals.run --suite smoke
python -m agent.evals.run --suite security
```
