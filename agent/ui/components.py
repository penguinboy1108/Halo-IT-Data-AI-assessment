"""Small Streamlit rendering helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from agent.models import AgentResponse

RATE_COLUMNS = {"sla_compliance_rate", "escalation_rate", "csat_response_rate"}
METRIC_PREFERENCE = [
    "ticket_count",
    "sla_compliance_rate",
    "median_resolution_hours",
    "median_first_response_hours",
    "average_csat",
    "escalation_rate",
    "percentage_of_tickets",
    "value",
]


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(column) for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]


def _metric_column(df: pd.DataFrame, numeric_columns: list[str]) -> str | None:
    for column in METRIC_PREFERENCE:
        if column in numeric_columns:
            return column
    return numeric_columns[0] if numeric_columns else None


def _dimension_columns(df: pd.DataFrame, numeric_columns: list[str]) -> list[str]:
    return [str(column) for column in df.columns if str(column) not in numeric_columns]


def _chart_frame(df: pd.DataFrame, metric: str, dimensions: list[str]) -> pd.DataFrame:
    chart_df = df.copy()
    if "created_month" in chart_df.columns:
        chart_df = chart_df.sort_values("created_month")

    if "created_month_name" in chart_df.columns:
        chart_df["chart_label"] = chart_df["created_month_name"].astype(str)
    elif len(dimensions) >= 2:
        chart_df["chart_label"] = (
            chart_df[dimensions[0]].astype(str) + " / " + chart_df[dimensions[1]].astype(str)
        )
    elif dimensions:
        chart_df["chart_label"] = chart_df[dimensions[0]].astype(str)
    else:
        chart_df["chart_label"] = chart_df.index.astype(str)

    chart_metric = metric
    if metric in RATE_COLUMNS and chart_df[metric].dropna().between(-1, 1).all():
        chart_metric = f"{metric}_pct"
        chart_df[chart_metric] = chart_df[metric] * 100

    return chart_df[["chart_label", chart_metric]].rename(
        columns={"chart_label": "Segment", chart_metric: metric.replace("_", " ").title()}
    )


def _render_query_result(response: AgentResponse) -> None:
    if not response.query_result or not response.query_result.rows:
        return

    df = pd.DataFrame(response.query_result.rows)
    st.subheader("Query result")
    st.dataframe(df, use_container_width=True, hide_index=True)

    numeric_columns = _numeric_columns(df)
    metric = _metric_column(df, numeric_columns)
    if metric is None:
        return

    dimensions = _dimension_columns(df, numeric_columns)
    chart_df = _chart_frame(df, metric, dimensions)
    chart_df = chart_df.set_index("Segment")
    st.subheader("Result chart")
    if "created_month" in df.columns:
        st.line_chart(chart_df, use_container_width=True)
    else:
        st.bar_chart(chart_df, use_container_width=True)
    st.caption("Chart generated from the structured DuckDB query result.")


def _provenance_payload(response: AgentResponse) -> dict[str, Any]:
    if not response.answer:
        return {}
    return {
        "query_id": response.answer.query_id,
        "rows_analysed": response.answer.rows_analysed,
        "dataset_version": response.answer.dataset_version,
        "confidence": response.answer.confidence,
        "filters": response.answer.filters_applied,
        "state": response.state,
        "tokens": response.usage.total_tokens,
        "estimated_cost_usd": round(response.usage.estimated_cost_usd, 6),
        "value_per_1k_tokens": round(response.value_per_1k_tokens, 4),
    }


def render_response(response: AgentResponse) -> None:
    if response.refusal_reason:
        st.warning(response.refusal_reason)
        return
    if not response.answer:
        st.error("The agent did not produce an answer.")
        return

    st.markdown(response.answer.answer_markdown)
    if response.answer.evidence:
        evidence_df = pd.DataFrame([item.model_dump() for item in response.answer.evidence])
        st.dataframe(evidence_df, use_container_width=True, hide_index=True)

    _render_query_result(response)

    with st.expander("Query provenance"):
        st.write(_provenance_payload(response))
        if response.sql:
            st.code(response.sql, language="sql")
