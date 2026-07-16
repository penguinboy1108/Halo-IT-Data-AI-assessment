"""Tiny programmatic API for the agent."""

from agent.orchestrator import AnalyticsOrchestrator


def ask(question: str) -> str:
    response = AnalyticsOrchestrator().answer(question)
    if response.answer:
        return response.answer.answer_markdown
    return response.refusal_reason or "The agent could not answer the question."
