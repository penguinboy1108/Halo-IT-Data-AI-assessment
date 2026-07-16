"""Offline eval runner using the deterministic fake path."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from agent.orchestrator import AnalyticsOrchestrator
from agent.state import AgentState


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="smoke")
    parser.add_argument("--cases", type=Path, default=Path("agent/evals/cases.yaml"))
    args = parser.parse_args()
    del args.suite

    cases = yaml.safe_load(args.cases.read_text(encoding="utf-8"))["cases"]
    orchestrator = AnalyticsOrchestrator()
    failures = []
    for case in cases:
        response = orchestrator.answer(case["question"])
        if case.get("must_refuse") and response.state != AgentState.REFUSED:
            failures.append(case["id"])
        if not case.get("must_refuse") and response.state == AgentState.REFUSED:
            failures.append(case["id"])
    if failures:
        raise SystemExit(f"Eval failures: {failures}")
    print(f"Passed {len(cases)} eval cases.")


if __name__ == "__main__":
    main()
