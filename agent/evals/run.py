"""Offline eval runner using the deterministic fake path."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from agent.orchestrator import AnalyticsOrchestrator
from agent.settings import Settings
from agent.state import AgentState

SECURITY_KEYWORDS = {
    "injection",
    "secret",
    "filesystem",
    "prompt",
    "personal",
    "destructive",
    "copy",
    "install",
    "attach",
    "raw_notes",
    "hidden",
    "python",
    "web",
}


def _select_cases(cases: list[dict[str, object]], suite: str) -> list[dict[str, object]]:
    if suite == "smoke":
        return cases
    if suite == "security":
        return [
            case
            for case in cases
            if case.get("must_refuse")
            or any(keyword in str(case.get("id", "")) for keyword in SECURITY_KEYWORDS)
        ]
    raise SystemExit(f"Unknown eval suite: {suite}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="smoke")
    parser.add_argument("--cases", type=Path, default=Path("agent/evals/cases.yaml"))
    args = parser.parse_args()
    cases = _select_cases(
        yaml.safe_load(args.cases.read_text(encoding="utf-8"))["cases"], args.suite
    )
    orchestrator = AnalyticsOrchestrator(Settings(AGENT_LLM_MODE="fake"))
    failures = []
    for case in cases:
        response = orchestrator.answer(str(case["question"]))
        if case.get("must_refuse") and response.state != AgentState.REFUSED:
            failures.append(case["id"])
        if not case.get("must_refuse") and response.state == AgentState.REFUSED:
            failures.append(case["id"])
    if failures:
        raise SystemExit(f"Eval failures: {failures}")
    print(f"Passed {len(cases)} eval cases.")


if __name__ == "__main__":
    main()
