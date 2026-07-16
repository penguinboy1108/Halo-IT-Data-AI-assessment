"""Evaluator role."""

from __future__ import annotations

from agent.models import EvaluationResult, FinalAnswerDraft


class EvaluatorAgent:
    def evaluate(self, answer: FinalAnswerDraft) -> EvaluationResult:
        issues: list[str] = []
        if not answer.query_id:
            issues.append("Missing query ID.")
        if not answer.evidence:
            issues.append("Missing evidence.")
        if (
            "customer_email" in answer.answer_markdown.lower()
            or "groq_api_key" in answer.answer_markdown.lower()
        ):
            issues.append("Unsafe disclosure term appeared in answer.")

        hard_fail = bool(issues)
        score = 0.0 if hard_fail else 0.92
        return EvaluationResult(
            correctness=score,
            groundedness=score,
            completeness=0.88 if not hard_fail else 0.0,
            relevance=0.9 if not hard_fail else 0.0,
            safety=1.0 if not hard_fail else 0.0,
            caveat_quality=0.86 if not hard_fail else 0.0,
            actionability=0.84 if not hard_fail else 0.0,
            cost_efficiency=0.95,
            hard_fail=hard_fail,
            issues=issues,
            suggested_revision=None
            if not hard_fail
            else "Regenerate with evidence and safe provenance.",
            retry_required=hard_fail,
        )
