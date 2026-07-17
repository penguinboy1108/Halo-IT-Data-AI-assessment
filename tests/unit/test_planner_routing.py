from agent.agents.planner import PlannerAgent
from agent.agents.sql_producer import SQLProducerAgent


def test_resolution_time_by_priority_routes_to_priority() -> None:
    plan = PlannerAgent().plan("Compare resolution time by priority")

    assert plan.dimensions == ["priority"]
    assert "median_resolution_hours" in plan.metrics

    candidate = SQLProducerAgent().produce(plan)
    assert "GROUP BY priority" in candidate.sql
    assert "MEDIAN(resolution_time_hours)" in candidate.sql
    assert candidate.expected_columns == [
        "priority",
        "ticket_count",
        "median_resolution_hours",
        "sla_compliance_rate",
    ]


def test_team_sla_question_routes_to_team() -> None:
    plan = PlannerAgent().plan("Which team has the lowest SLA compliance?")

    assert plan.dimensions == ["team"]
    candidate = SQLProducerAgent().produce(plan)
    assert "GROUP BY team" in candidate.sql


def test_urgent_low_comparison_keeps_priority_filter() -> None:
    plan = PlannerAgent().plan("Compare urgent and low priority ticket performance")
    candidate = SQLProducerAgent().produce(plan)

    assert plan.dimensions == ["priority"]
    assert "priority IN ('Urgent', 'Low')" in candidate.sql
