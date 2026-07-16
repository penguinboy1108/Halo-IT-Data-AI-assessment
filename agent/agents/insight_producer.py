"""Insight producer role."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from agent.models import AnalysisPlan, EvidenceItem, FinalAnswerDraft, QueryResult

RATE_COLUMNS = {
    "sla_compliance_rate",
    "escalation_rate",
    "csat_response_rate",
    "percentage_of_tickets",
}
DIMENSION_HINTS = {
    "created_month",
    "created_month_name",
    "created_year",
    "holiday_period",
    "metric",
    "priority",
    "region",
    "reporting_category",
    "reporting_subcategory",
    "service_area",
    "subscription_type",
    "team",
}
METRIC_KEYWORDS = (
    "count",
    "rate",
    "hours",
    "csat",
    "percentage",
    "tickets",
    "value",
)


def _normalise_column(column: str) -> str:
    return column.lower().strip()


def _coerce_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float | Decimal):
        return float(value)
    return None


def _is_rate_column(column: str) -> bool:
    return _normalise_column(column) in RATE_COLUMNS or _normalise_column(column).endswith("_rate")


def _is_count_column(column: str) -> bool:
    lowered = _normalise_column(column)
    return lowered.endswith("_count") or lowered in {"ticket_count", "value"}


def _is_metric_column(column: str) -> bool:
    lowered = _normalise_column(column)
    if lowered in DIMENSION_HINTS:
        return False
    return any(keyword in lowered for keyword in METRIC_KEYWORDS)


def _format_value(column: str, value: Any) -> str:
    number = _coerce_number(value)
    if number is None:
        return "n/a" if value is None else str(value)
    if _is_rate_column(column):
        percentage = number * 100 if -1 <= number <= 1 else number
        return f"{percentage:.1f}%"
    if "hours" in _normalise_column(column):
        return f"{number:,.1f} hours"
    if "csat" in _normalise_column(column):
        return f"{number:.2f}/5"
    if _is_count_column(column) or number.is_integer():
        return f"{number:,.0f}"
    return f"{number:,.2f}"


def _format_label(column: str) -> str:
    return column.replace("_", " ").title()


def _format_row(row: dict[str, Any], columns: list[str]) -> str:
    return ", ".join(f"{_format_label(key)}: {_format_value(key, row.get(key))}" for key in columns)


def _metric_columns(columns: list[str], rows: list[dict[str, Any]]) -> list[str]:
    metrics: list[str] = []
    for column in columns:
        looks_metric = _is_metric_column(column) or any(
            _coerce_number(row.get(column)) is not None for row in rows
        )
        if looks_metric and _normalise_column(column) not in DIMENSION_HINTS:
            metrics.append(column)
    return metrics


def _dimension_columns(columns: list[str], metric_columns: list[str]) -> list[str]:
    return [column for column in columns if column not in metric_columns]


def _primary_metric(plan: AnalysisPlan, columns: list[str], metrics: list[str]) -> str | None:
    metric_lookup = {column.lower(): column for column in metrics}
    for sort_item in plan.sort:
        sort_column = sort_item.split()[0].lower()
        if sort_column in metric_lookup:
            return metric_lookup[sort_column]

    aliases = {
        "total_tickets": "ticket_count",
        "data_quality_summary": "percentage_of_tickets",
    }
    for metric in plan.metrics:
        candidate = aliases.get(metric, metric).lower()
        if candidate in metric_lookup:
            return metric_lookup[candidate]

    for preferred in (
        "sla_compliance_rate",
        "ticket_count",
        "median_resolution_hours",
        "median_first_response_hours",
        "average_csat",
        "escalation_rate",
        "percentage_of_tickets",
    ):
        if preferred in metric_lookup:
            return metric_lookup[preferred]
    return metrics[0] if metrics else (columns[-1] if columns else None)


def _sort_rows_for_signal(
    rows: list[dict[str, Any]], metric: str, plan: AnalysisPlan
) -> list[dict[str, Any]]:
    if not rows:
        return []
    sort_directives = [
        item.lower() for item in plan.sort if item.lower().startswith(metric.lower())
    ]
    reverse = bool(sort_directives and "desc" in sort_directives[0])
    if not sort_directives and metric in {
        "ticket_count",
        "median_resolution_hours",
        "percentage_of_tickets",
    }:
        reverse = True
    return sorted(
        rows,
        key=lambda row: _coerce_number(row.get(metric)) or 0.0,
        reverse=reverse,
    )


def _markdown_table(rows: list[dict[str, Any]], columns: list[str], max_rows: int = 6) -> str:
    if not rows:
        return "No result rows were returned."
    limited_rows = rows[:max_rows]
    headers = [_format_label(column) for column in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in limited_rows:
        values = [
            str(_format_value(column, row.get(column))).replace("|", "\\|") for column in columns
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _row_identity(row: dict[str, Any], dimensions: list[str]) -> str:
    labels = [str(row.get(column)) for column in dimensions[:2] if row.get(column) is not None]
    return " / ".join(labels) if labels else "the leading result"


def _trend_finding(rows: list[dict[str, Any]], metric: str) -> str:
    sorted_rows = sorted(rows, key=lambda row: _coerce_number(row.get("created_month")) or 0.0)
    values = [(row, _coerce_number(row.get(metric))) for row in sorted_rows]
    numeric_values = [(row, value) for row, value in values if value is not None]
    if not numeric_values:
        return "The monthly trend query returned rows, but no numeric metric was available."

    peak_row, peak_value = max(numeric_values, key=lambda item: item[1])
    low_row, low_value = min(numeric_values, key=lambda item: item[1])
    first_value = numeric_values[0][1]
    last_value = numeric_values[-1][1]
    direction = (
        "increased"
        if last_value > first_value
        else "decreased"
        if last_value < first_value
        else "was flat"
    )
    peak_label = (
        peak_row.get("created_month_name") or peak_row.get("created_month") or "the peak month"
    )
    low_label = (
        low_row.get("created_month_name") or low_row.get("created_month") or "the lowest month"
    )
    return (
        f"Monthly {_format_label(metric).lower()} {direction} from "
        f"{_format_value(metric, first_value)} to {_format_value(metric, last_value)}. "
        f"The peak was {peak_label} at {_format_value(metric, peak_value)}, while the low point "
        f"was {low_label} at {_format_value(metric, low_value)}."
    )


def _finding(
    plan: AnalysisPlan, result: QueryResult, metric: str | None, dimensions: list[str]
) -> str:
    if not result.rows:
        return "The dataset returned no rows for the requested analysis."
    if metric is None:
        return f"Top result: {_format_row(result.rows[0], result.columns)}."
    if "created_month" in result.columns:
        return _trend_finding(result.rows, metric)

    signal_rows = _sort_rows_for_signal(result.rows, metric, plan)
    signal = signal_rows[0]
    identity = _row_identity(signal, dimensions)
    metric_label = _format_label(metric).lower()
    metric_value = _format_value(metric, signal.get(metric))

    if _is_rate_column(metric) and "sla" in _normalise_column(metric):
        return f"{identity} is the weakest SLA signal in this result set at {metric_value}."
    if "resolution" in _normalise_column(metric) or "response" in _normalise_column(metric):
        return f"{identity} shows the slowest {metric_label} in this result set at {metric_value}."
    if "csat" in _normalise_column(metric):
        return f"{identity} is the most important CSAT signal in this result set at {metric_value}."
    if result.columns[:2] == ["metric", "value"]:
        return f"{identity} is a material data-quality signal with value {metric_value}."
    return f"{identity} is the leading signal for {metric_label} at {metric_value}."


def _business_interpretation(plan: AnalysisPlan, columns: list[str]) -> str:
    lowered_columns = {_normalise_column(column) for column in columns}
    if "team" in lowered_columns:
        return (
            "For management, this is a queue health signal rather than a staff "
            "performance verdict. A low team-level SLA rate could reflect case mix, "
            "backlog age, hand-offs, holiday cover, or SLA targets that do not match "
            "the work entering that queue."
        )
    if "holiday_period" in lowered_columns:
        return (
            "Holiday comparisons are useful for capacity planning. Differences around "
            "public holidays could point to reduced staffing, backlog accumulation "
            "before or after holidays, or customer availability patterns, but this "
            "dataset alone does not prove that holidays caused the change."
        )
    if "created_month" in lowered_columns:
        return (
            "The monthly pattern is a demand signal. Peaks can align with releases, "
            "onboarding waves, renewals, campaigns, or seasonal customer behaviour, "
            "so the chart should be reviewed beside release and staffing calendars."
        )
    if {"reporting_category", "reporting_subcategory"} & lowered_columns:
        return (
            "Category-level resolution time highlights where support effort may be "
            "blocked by product complexity, missing knowledge articles, unclear "
            "ownership, or dependency on another team."
        )
    if "service_area" in lowered_columns:
        return (
            "A high-volume service area with weaker CSAT is a customer-experience "
            "risk. It can indicate repeat friction in the service design, slow "
            "escalation paths, unclear communications, or a product area generating "
            "preventable demand."
        )
    if plan.intent == "data_quality":
        return (
            "These quality issues affect trust in the dashboard and agent answers. "
            "The safest reporting approach is to keep source fields visible, use "
            "calculated reporting fields, and track quality flags as first-class "
            "metrics."
        )
    if "priority" in lowered_columns:
        return (
            "Priority comparisons help test whether triage rules are working. "
            "Unexpected differences may mean priority is being assigned inconsistently, "
            "old low-priority work is accumulating, or urgent work still has routing "
            "delays."
        )
    return (
        "This should be read as an operational signal from the reporting-ready 2024-2025 dataset, "
        "not as proof of causality."
    )


def _possible_drivers(plan: AnalysisPlan, columns: list[str]) -> list[str]:
    lowered_columns = {_normalise_column(column) for column in columns}
    if "team" in lowered_columns:
        return [
            "Different teams may be receiving different category, priority, or complexity mixes.",
            "Work could be delayed by cross-team hand-offs, approval waits, or unclear ownership.",
            (
                "Capacity may not match arrival patterns, especially around leave, "
                "holidays, and peak months."
            ),
            "The SLA target may be stricter for the work assigned to the lowest-compliance queue.",
        ]
    if "holiday_period" in lowered_columns:
        return [
            "Holiday cover may reduce first-response or resolution capacity.",
            "Backlog may build before holidays and surface on the day after a holiday.",
            "Customers may reply more slowly during holidays, stretching apparent resolution time.",
            "Holiday rows are usually a smaller sample, so use confidence cautiously.",
        ]
    if "created_month" in lowered_columns:
        return [
            "Product releases, migrations, onboarding waves, or campaigns may create spikes.",
            "Seasonal customer activity can change demand without any process failure.",
            "A month with high volume and lower SLA should be checked against staffing rosters.",
        ]
    if {"reporting_category", "reporting_subcategory"} & lowered_columns:
        return [
            (
                "Long-running categories may need engineering/vendor input rather "
                "than pure support effort."
            ),
            (
                "Ambiguous categorisation can route tickets to the wrong team before "
                "resolution starts."
            ),
            "Missing self-service content can create repeat tickets and avoidable workload.",
        ]
    if "service_area" in lowered_columns:
        return [
            "High contact volume can come from confusing product flows or unclear guidance.",
            "Low CSAT may reflect repeated updates without resolution, not just speed.",
            "Escalation rate can reveal where frontline teams lack authority or tooling.",
        ]
    if plan.intent == "data_quality":
        return [
            (
                "Legacy aliases and free-text categories likely explain part of the "
                "category mismatch volume."
            ),
            "Manual status updates can drift from resolved dates and calculated SLA outcomes.",
            "Timestamps may be coming from multiple systems with different validation rules.",
        ]
    return [
        "Case mix, seasonality, priority assignment, backlog age, and routing should be checked "
        "before treating the result as a root cause.",
        "Compare by priority, category, holiday period, and month to separate demand "
        "effects from process issues.",
    ]


def _recommended_actions(
    plan: AnalysisPlan, rows: list[dict[str, Any]], dimensions: list[str]
) -> list[str]:
    focus = _row_identity(rows[0], dimensions) if rows else "the leading segment"
    if plan.intent == "data_quality":
        return [
            "Create a data-quality scorecard for category mismatch, SLA flag, date validity, "
            "and reporting eligibility.",
            "Use calculated SLA and reporting category fields in Power BI and the agent "
            "until source-system rules are corrected.",
            "Assign ownership for the top two defects and review counts after each refresh.",
        ]
    if "holiday_period" in dimensions:
        return [
            "Add a holiday drill-through showing volume, response time, and SLA by window.",
            "Compare holiday queues against staffing rosters and backlog entering the day.",
            "Pilot a coverage rule for the highest-risk window and monitor SLA for four weeks.",
        ]
    return [
        (
            f"Drill into {focus} by priority, reporting category, month, and holiday "
            "period before assigning cause."
        ),
        (
            "Sample 20-30 tickets from the segment to identify repeat failure modes "
            "and ownership blockers."
        ),
        (
            "Pick one experiment, such as routing cleanup, knowledge-base improvement, "
            "or roster adjustment, "
            "and track SLA/CSAT impact in the next refresh."
        ),
    ]


def _confidence(result: QueryResult) -> Literal["low", "medium", "high"]:
    if not result.rows:
        return "medium"
    if result.source_row_count >= 1000 and result.row_count >= 2:
        return "high"
    if result.source_row_count >= 100:
        return "medium"
    return "low"


class InsightProducerAgent:
    def draft(
        self, question: str, plan: AnalysisPlan, result: QueryResult, caveats: list[str]
    ) -> FinalAnswerDraft:
        del question
        top_rows = result.rows[:3]
        metrics = _metric_columns(result.columns, result.rows)
        dimensions = _dimension_columns(result.columns, metrics)
        primary_metric = _primary_metric(plan, result.columns, metrics)
        finding = _finding(plan, result, primary_metric, dimensions)

        evidence = [
            EvidenceItem(
                claim=f"Result row {idx + 1}",
                value=_format_row(row, result.columns),
                source_column_or_metric=", ".join(result.columns),
            )
            for idx, row in enumerate(top_rows)
        ]
        if not evidence:
            evidence = [
                EvidenceItem(
                    claim="No rows returned",
                    value="0",
                    source_column_or_metric=", ".join(result.columns),
                )
            ]

        interpretation = _business_interpretation(plan, result.columns)
        possible_drivers = _possible_drivers(plan, result.columns)
        actions = _recommended_actions(plan, result.rows, dimensions)
        caveat_text = caveats or [
            (
                "Uses reporting_eligible_flag = TRUE unless the query is explicitly "
                "about data quality."
            ),
            (
                "SLA compliance uses calculated_sla_breached because the source SLA "
                "flag is inconsistent."
            ),
            "Operational comparisons show association, not proven causality.",
        ]

        answer_markdown = "\n\n".join(
            [
                f"**Finding**\n{finding}",
                "**Evidence table**\n" + _markdown_table(result.rows, result.columns),
                f"**Business interpretation**\n{interpretation}",
                "**Possible drivers to investigate**\n"
                + "\n".join(f"- {driver}" for driver in possible_drivers),
                "**Recommended actions**\n"
                + "\n".join(f"{idx + 1}. {action}" for idx, action in enumerate(actions)),
                "**Caveats**\n" + "\n".join(f"- {item}" for item in caveat_text),
                "**Provenance**\n"
                f"- Query ID: `{result.query_id}`\n"
                f"- Rows analysed: `{result.source_row_count}` source rows, "
                f"`{result.row_count}` result rows\n"
                f"- Dataset version: `{result.dataset_version}`\n"
                f"- SQL hash: `{result.sql_hash}`",
            ]
        )
        return FinalAnswerDraft(
            finding=finding,
            evidence=evidence,
            operational_interpretation=interpretation,
            recommended_action="\n".join(actions),
            caveats=caveat_text,
            filters_applied=plan.filters,
            rows_analysed=result.source_row_count,
            query_id=result.query_id,
            dataset_version=result.dataset_version,
            confidence=_confidence(result),
            answer_markdown=answer_markdown,
        )
