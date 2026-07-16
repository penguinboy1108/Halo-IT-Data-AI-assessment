# Evaluation Methodology

The v1 evaluation suite is offline and deterministic. It verifies that normal demo questions complete and high-risk security questions are refused without requiring a live Groq key.

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
