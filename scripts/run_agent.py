"""CLI entry point for quick local agent checks."""

from __future__ import annotations

import argparse
import sys

from agent.orchestrator import AnalyticsOrchestrator


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    _configure_stdout()
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="+")
    args = parser.parse_args()
    response = AnalyticsOrchestrator().answer(" ".join(args.question))
    if response.answer:
        print(response.answer.answer_markdown)
    else:
        print(response.refusal_reason or "No answer produced.")


if __name__ == "__main__":
    main()
