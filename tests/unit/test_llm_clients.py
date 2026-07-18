from types import SimpleNamespace

from agent.llm.fake_client import FakeStructuredLLMClient
from agent.llm.groq_client import GroqJSONClient
from agent.models import AnalysisPlan
from agent.settings import Settings


def _plan() -> AnalysisPlan:
    return AnalysisPlan(
        answerable=True,
        intent="comparison",
        metrics=["total_tickets"],
        dimensions=["team"],
        expected_output="Rank teams.",
    )


def test_fake_structured_client_returns_validated_model():
    client = FakeStructuredLLMClient([_plan()])

    completion = client.complete_model(
        system_prompt="system",
        user_prompt="user",
        response_model=AnalysisPlan,
        max_tokens=100,
        reasoning_effort="low",
        temperature=0.0,
        role="planner",
        prompt_version="v1",
    )

    assert completion.value.intent == "comparison"
    assert completion.usage.total_tokens > 0
    assert completion.prompt_version == "v1"


def test_groq_client_validates_json_and_provider_usage(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=_plan().model_dump_json()))
                ],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            )

    class FakeGroq:
        def __init__(self, api_key):
            assert api_key == "gsk_test"
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("agent.llm.groq_client.Groq", FakeGroq)
    settings = Settings(AGENT_LLM_MODE="groq", GROQ_API_KEY="gsk_test")

    completion = GroqJSONClient(settings).complete_model(
        system_prompt="system",
        user_prompt="user",
        response_model=AnalysisPlan,
        max_tokens=100,
        reasoning_effort="low",
        temperature=0.0,
        role="planner",
        prompt_version="v1",
    )

    assert completion.value.intent == "comparison"
    system_message = captured["messages"][0]["content"]
    assert "JSON object" in system_message
    assert captured["response_format"] == {"type": "json_object"}
    assert completion.usage.prompt_tokens == 10
    assert completion.usage.completion_tokens == 5
    assert completion.usage.source == "provider"
