from agent.llm.prompts import load_prompt, prompt_versions


def test_prompt_versions_are_configured():
    versions = prompt_versions()

    assert versions["planner"] == "v1"
    assert versions["sql_producer"] == "v1"
    assert versions["insight_producer"] == "v1"
    assert versions["evaluator"] == "v1"


def test_load_prompt_returns_text_and_version():
    prompt, version = load_prompt("planner")

    assert "Planning Agent" in prompt
    assert version == "v1"
