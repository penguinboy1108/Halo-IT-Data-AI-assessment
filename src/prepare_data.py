"""Part 1 data preparation for the Halo IT Data & AI assessment."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TICKETS = ROOT / "data" / "raw" / "TechSolve - Ticket Data.xlsx"
DEFAULT_HOLIDAYS = ROOT / "data" / "raw" / "nz_public_holidays.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed"

REPORTING_START = pd.Timestamp("2024-01-01")
REPORTING_END = pd.Timestamp("2025-12-31")
PLAUSIBLE_START = pd.Timestamp("2023-01-01")
PLAUSIBLE_END = pd.Timestamp("2025-12-31")


def clean_key(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", text)


CATEGORY_ALIAS = {
    "account suspension": "Account Suspension",
    "acct suspension": "Account Suspension",
    "bug": "Bug Report",
    "bug report": "Bug Report",
    "data sync": "Data Sync Issue",
    "data sync issue": "Data Sync Issue",
    "feature req": "Feature Request",
    "feature request": "Feature Request",
    "login issue": "Login Issue",
    "payment problem": "Payment Problem",
    "performance issue": "Performance Issue",
    "perf issue": "Performance Issue",
    "refund req": "Refund Request",
    "refund request": "Refund Request",
    "security": "Security Concern",
    "security concern": "Security Concern",
    "sub cancellation": "Subscription Cancellation",
    "subscription cancel": "Subscription Cancellation",
    "subscription cancellation": "Subscription Cancellation",
}


SOURCE_CATEGORY_TO_REPORTING = {
    "Account Suspension": "Access & Security",
    "Login Issue": "Access & Security",
    "Security Concern": "Access & Security",
    "Payment Problem": "Billing & Payments",
    "Refund Request": "Billing & Payments",
    "Bug Report": "Product Reliability",
    "Performance Issue": "Product Reliability",
    "Data Sync Issue": "Data & Integration",
    "Subscription Cancellation": "Subscription Management",
    "Feature Request": "Product Improvement",
}


ISSUE_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("two-factor", "authentication codes", "2fa"), "Access & Security", "MFA Failure"),
    (("unable to access", "correct credentials", "login"), "Access & Security", "Login Failure"),
    (("payment was deducted", "transaction shows failed"), "Billing & Payments", "Failed Payment"),
    (("billing statement", "discrepancy"), "Billing & Payments", "Billing Dispute"),
    (("refund", "recent charge"), "Billing & Payments", "Refund Request"),
    (("crashes", "upload a file"), "Product Reliability", "Application Crash"),
    (("slow performance", "dashboard"), "Product Reliability", "Performance Degradation"),
    (("not syncing", "syncing data", "across devices"), "Data & Integration", "Data Synchronization"),
    (("subscription was cancelled", "without my request"), "Subscription Management", "Unexpected Cancellation"),
    (("bug", "report generation"), "Product Reliability", "Reporting Bug"),
]


STATUS_CLOSED = {"Closed", "Resolved"}
STATUS_OPEN = {"Open", "In Progress", "Pending Customer"}


def classify_issue(description: object) -> tuple[str, str]:
    text = clean_key(description)
    for patterns, category, subcategory in ISSUE_RULES:
        if any(pattern in text for pattern in patterns):
            return category, subcategory
    return "Unclassified", "Unclassified"


def yes_no_to_bool(value: object) -> pd.BooleanDtype:
    key = clean_key(value)
    if key == "yes":
        return True
    if key == "no":
        return False
    return pd.NA


def bucket_hours(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    hours = float(value)
    if hours < 4:
        return "0-4 hours"
    if hours < 8:
        return "4-8 hours"
    if hours < 24:
        return "8-24 hours"
    if hours < 72:
        return "1-3 days"
    if hours < 168:
        return "3-7 days"
    return "7+ days"


def value_band(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    amount = float(value)
    if amount <= 0:
        return "Free / zero value"
    if amount < 100:
        return "Under 100"
    if amount < 500:
        return "100-499"
    if amount < 1000:
        return "500-999"
    return "1000+"


def complexity_bucket(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    score = int(value)
    if score <= 3:
        return "Low"
    if score <= 6:
        return "Medium"
    return "High"


def load_holidays(path: Path) -> pd.DataFrame:
    holidays = pd.read_csv(path)
    holidays["holiday_date"] = pd.to_datetime(holidays["holiday_date"], errors="coerce")
    holidays = holidays.dropna(subset=["holiday_date", "holiday_name"]).copy()
    holidays["holiday_date"] = holidays["holiday_date"].dt.normalize()
    holidays["year"] = holidays["holiday_date"].dt.year
    return holidays.sort_values(["holiday_date", "holiday_name"]).reset_index(drop=True)


def aggregate_holidays(holidays: pd.DataFrame) -> pd.DataFrame:
    return (
        holidays.groupby("holiday_date", as_index=False)
        .agg(
            holiday_name=("holiday_name", lambda s: "; ".join(sorted(set(map(str, s))))),
            holiday_scope=("scope", lambda s: "; ".join(sorted(set(map(str, s))))),
        )
        .sort_values("holiday_date")
    )


def nearest_holiday_lookup(dates: Iterable[pd.Timestamp], holidays: pd.DataFrame) -> pd.DataFrame:
    holiday_dates = holidays["holiday_date"].drop_duplicates().sort_values().tolist()
    holiday_names = holidays.drop_duplicates("holiday_date").set_index("holiday_date")["holiday_name"].to_dict()

    rows = []
    for date in dates:
        if not holiday_dates:
            rows.append((date, np.nan, ""))
            continue
        distances = [abs((holiday - date).days) for holiday in holiday_dates]
        idx = int(np.argmin(distances))
        nearest = holiday_dates[idx]
        rows.append((date, int(distances[idx]), holiday_names.get(nearest, "")))
    return pd.DataFrame(rows, columns=["date", "days_from_nearest_holiday", "nearest_holiday_name"])


def build_date_dimension(holidays: pd.DataFrame) -> pd.DataFrame:
    start = PLAUSIBLE_START
    end = PLAUSIBLE_END
    dates = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    iso = dates["date"].dt.isocalendar()
    dates["year"] = dates["date"].dt.year
    dates["quarter"] = dates["date"].dt.quarter
    dates["month"] = dates["date"].dt.month
    dates["month_name"] = dates["date"].dt.month_name()
    dates["iso_week"] = iso.week.astype("int64")
    dates["day_of_week"] = dates["date"].dt.day_name()
    dates["is_weekend"] = dates["date"].dt.dayofweek >= 5

    holiday_by_date = aggregate_holidays(holidays)
    dates = dates.merge(holiday_by_date, left_on="date", right_on="holiday_date", how="left")
    dates = dates.drop(columns=["holiday_date"])
    dates["is_public_holiday"] = dates["holiday_name"].notna()

    holiday_dates = set(holiday_by_date["holiday_date"])
    dates["is_day_before_holiday"] = dates["date"].isin({d - pd.Timedelta(days=1) for d in holiday_dates})
    dates["is_day_after_holiday"] = dates["date"].isin({d + pd.Timedelta(days=1) for d in holiday_dates})
    dates["holiday_period"] = np.select(
        [
            dates["is_public_holiday"],
            dates["is_day_before_holiday"],
            dates["is_day_after_holiday"],
        ],
        ["Public holiday", "Day before holiday", "Day after holiday"],
        default="Regular day",
    )
    dates = dates.merge(nearest_holiday_lookup(dates["date"], holiday_by_date), on="date", how="left")
    return dates


def add_date_fields(df: pd.DataFrame) -> pd.DataFrame:
    df["created_at"] = pd.to_datetime(df["ticket_created_date"], errors="coerce")
    df["resolved_at"] = pd.to_datetime(df["ticket_resolved_date"], errors="coerce")
    df["account_created_at"] = pd.to_datetime(df["account_created_date"], errors="coerce")

    df["created_date"] = df["created_at"].dt.normalize()
    df["resolved_date"] = df["resolved_at"].dt.normalize()
    iso = df["created_at"].dt.isocalendar()
    df["created_year"] = df["created_at"].dt.year.astype("Int64")
    df["created_quarter"] = df["created_at"].dt.quarter.astype("Int64")
    df["created_month"] = df["created_at"].dt.month.astype("Int64")
    df["created_month_name"] = df["created_at"].dt.month_name()
    df["created_iso_week"] = iso.week.astype("Int64")
    df["created_day_of_week"] = df["created_at"].dt.day_name()
    df["created_hour"] = df["created_at"].dt.hour.astype("Int64")
    df["is_weekend"] = df["created_at"].dt.dayofweek >= 5
    df["resolution_days"] = df["resolution_time_hours"] / 24
    return df


def add_category_fields(df: pd.DataFrame) -> pd.DataFrame:
    df["source_category_key"] = df["source_category"].map(clean_key)
    df["source_category_standard"] = df["source_category_key"].map(CATEGORY_ALIAS).fillna("Unmapped")
    df["source_reporting_category"] = (
        df["source_category_standard"].map(SOURCE_CATEGORY_TO_REPORTING).fillna("Unmapped")
    )

    classified = df["issue_description"].apply(classify_issue)
    df["reporting_category"] = classified.map(lambda x: x[0])
    df["reporting_subcategory"] = classified.map(lambda x: x[1])
    df["category_mismatch_flag"] = df["source_reporting_category"] != df["reporting_category"]
    return df


def add_quality_and_metric_fields(df: pd.DataFrame, date_dim: pd.DataFrame) -> pd.DataFrame:
    df["plausible_created_date_flag"] = df["created_date"].between(PLAUSIBLE_START, PLAUSIBLE_END)
    df["reporting_period_flag"] = df["created_date"].between(REPORTING_START, REPORTING_END)
    df["resolution_before_creation_flag"] = df["resolved_at"].notna() & (df["resolved_at"] < df["created_at"])
    df["valid_resolved_date_flag"] = df["resolved_at"].isna() | ~df["resolution_before_creation_flag"]
    df["status_date_consistency_flag"] = np.where(
        df["status"].isin(STATUS_CLOSED),
        df["resolved_at"].notna(),
        df["resolved_at"].isna(),
    )
    df["open_status_with_resolution_flag"] = df["status"].isin(STATUS_OPEN) & df["resolved_at"].notna()
    df["reporting_eligible_flag"] = (
        df["plausible_created_date_flag"] & df["reporting_period_flag"] & df["valid_resolved_date_flag"]
    )

    df["source_sla_breached_flag"] = df["source_sla_breached"].map(yes_no_to_bool).astype("boolean")
    df["calculated_sla_breached"] = df["resolution_time_hours"] > df["sla_target_hours"]
    df["sla_flag_mismatch"] = df["source_sla_breached_flag"].notna() & (
        df["source_sla_breached_flag"] != df["calculated_sla_breached"]
    )
    df["sla_variance_hours"] = df["resolution_time_hours"] - df["sla_target_hours"]
    df["sla_breach_severity"] = np.select(
        [
            df["sla_variance_hours"] <= 0,
            df["sla_variance_hours"] <= 4,
            df["sla_variance_hours"] <= 24,
            df["sla_variance_hours"] <= 72,
        ],
        ["Within SLA", "Minor breach", "Moderate breach", "Major breach"],
        default="Severe breach",
    )

    df["is_escalated"] = df["escalated"].map(yes_no_to_bool).astype("boolean")
    df["is_open_ticket"] = df["status"].isin(STATUS_OPEN)
    df["is_closed_ticket"] = df["status"].isin(STATUS_CLOSED)
    df["resolution_time_bucket"] = df["resolution_time_hours"].map(bucket_hours)
    df["first_response_bucket"] = df["first_response_time_hours"].map(bucket_hours)
    df["complexity_bucket"] = df["issue_complexity_score"].map(complexity_bucket)
    df["customer_value_band"] = df["monthly_contract_value"].map(value_band)
    df["repeat_customer_flag"] = df["previous_tickets"] > 0
    df["missing_team_or_assignee_flag"] = df["team"].isna() | df["assigned_to"].isna()
    df["csat_available_flag"] = df["csat_score"].notna()

    dim_cols = [
        "date",
        "is_public_holiday",
        "holiday_name",
        "holiday_scope",
        "is_day_before_holiday",
        "is_day_after_holiday",
        "holiday_period",
        "days_from_nearest_holiday",
        "nearest_holiday_name",
    ]
    df = df.merge(date_dim[dim_cols], left_on="created_date", right_on="date", how="left")
    df = df.drop(columns=["date"])
    df["is_public_holiday"] = df["is_public_holiday"].fillna(False)
    df["is_day_before_holiday"] = df["is_day_before_holiday"].fillna(False)
    df["is_day_after_holiday"] = df["is_day_after_holiday"].fillna(False)
    df["holiday_period"] = df["holiday_period"].fillna("Outside date dimension")

    return df


def add_clean_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    fill_map = {
        "company_name": "Unknown company",
        "industry": "Unknown industry",
        "account_manager": "Unassigned",
        "team": "Unassigned",
        "assigned_to": "Unassigned",
        "browser": "Unknown browser",
        "operating_system": "Unknown OS",
        "resolution_notes": "No resolution notes supplied",
    }
    for column, fallback in fill_map.items():
        df[f"{column}_clean"] = df[column].fillna(fallback)

    df["billing_contact_present_flag"] = df["billing_contact_email"].notna()
    df["customer_email_domain"] = df["customer_email"].astype(str).str.extract(r"@(.+)$", expand=False)
    df["customer_email_domain"] = df["customer_email_domain"].fillna("unknown")
    return df


def build_quality_summary(df: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    total = len(df)

    def row(metric: str, value: int | float, notes: str, pct_base: int | None = total) -> dict[str, object]:
        pct = "" if not pct_base else round(float(value) / pct_base * 100, 2)
        return {"metric": metric, "value": value, "percentage_of_tickets": pct, "notes": notes}

    rows = [
        row("source_rows", total, "Rows loaded from the source workbook."),
        row("source_columns", raw.shape[1], "Columns loaded from the source workbook.", None),
        row("duplicate_ticket_id_count", int(df["ticket_id"].duplicated().sum()), "Duplicate ticket identifiers."),
        row("raw_category_distinct_count", int(df["source_category"].nunique(dropna=True)), "Distinct raw category labels.", None),
        row(
            "standard_source_category_distinct_count",
            int(df["source_category_standard"].nunique(dropna=True)),
            "Distinct source categories after alias mapping.",
            None,
        ),
        row(
            "category_mismatch_count",
            int(df["category_mismatch_flag"].sum()),
            "Tickets where source category family differs from issue-description-derived reporting category.",
        ),
        row(
            "unclassified_issue_count",
            int((df["reporting_category"] == "Unclassified").sum()),
            "Issue descriptions that did not match the deterministic taxonomy rules.",
        ),
        row(
            "created_date_outside_2023_2025_count",
            int((~df["plausible_created_date_flag"]).sum()),
            "Created dates outside the plausible source coverage window.",
        ),
        row(
            "created_date_outside_reporting_period_2024_2025_count",
            int((~df["reporting_period_flag"]).sum()),
            "Rows retained but not eligible for the 2024-2025 dashboard period.",
        ),
        row(
            "resolution_before_creation_count",
            int(df["resolution_before_creation_flag"].sum()),
            "Resolved timestamp earlier than created timestamp.",
        ),
        row(
            "open_status_with_resolution_date_count",
            int(df["open_status_with_resolution_flag"].sum()),
            "Open/In Progress/Pending Customer tickets that still contain a resolved date.",
        ),
        row(
            "sla_flag_mismatch_count",
            int(df["sla_flag_mismatch"].sum()),
            "Source SLA breach flag disagrees with resolution_time_hours > sla_target_hours.",
        ),
        row(
            "missing_team_or_assignee_count",
            int(df["missing_team_or_assignee_flag"].sum()),
            "Tickets missing either team or assigned_to.",
        ),
        row("missing_csat_count", int((~df["csat_available_flag"]).sum()), "Tickets without a CSAT score."),
        row("public_holiday_ticket_count", int(df["is_public_holiday"].sum()), "Tickets created on a national public holiday."),
        row("reporting_eligible_count", int(df["reporting_eligible_flag"].sum()), "Rows recommended for the 2024-2025 dashboard."),
    ]
    return pd.DataFrame(rows)


def build_category_mapping(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["source_category", "source_category_standard", "source_reporting_category"], dropna=False)
        .size()
        .reset_index(name="ticket_count")
        .sort_values(["source_category_standard", "source_category"])
    )


def build_issue_taxonomy(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["issue_description", "reporting_category", "reporting_subcategory"], dropna=False)
        .size()
        .reset_index(name="ticket_count")
        .sort_values(["reporting_category", "reporting_subcategory", "issue_description"])
    )


def prepare(tickets_path: Path, holidays_path: Path, output_dir: Path) -> dict[str, object]:
    raw = pd.read_excel(tickets_path)
    df = raw.rename(columns={"category": "source_category", "sla_breached": "source_sla_breached"}).copy()

    holidays = load_holidays(holidays_path)
    date_dim = build_date_dimension(holidays)

    df = add_date_fields(df)
    df = add_category_fields(df)
    df = add_clean_text_fields(df)
    df = add_quality_and_metric_fields(df, date_dim)

    # Keep source data auditable while excluding direct email/name fields from the BI/AI dataset.
    drop_for_reporting = ["customer_name", "customer_email", "billing_contact_email"]
    tickets_cleaned = df.drop(columns=[c for c in drop_for_reporting if c in df.columns])

    output_dir.mkdir(parents=True, exist_ok=True)
    tickets_cleaned.to_csv(output_dir / "tickets_cleaned.csv", index=False)
    date_dim.to_csv(output_dir / "date_dimension.csv", index=False)
    build_quality_summary(df, raw).to_csv(output_dir / "data_quality_summary.csv", index=False)
    build_category_mapping(df).to_csv(output_dir / "category_mapping.csv", index=False)
    build_issue_taxonomy(df).to_csv(output_dir / "issue_taxonomy.csv", index=False)

    summary = {
        "source_rows": int(len(raw)),
        "source_columns": int(raw.shape[1]),
        "cleaned_rows": int(len(tickets_cleaned)),
        "cleaned_columns": int(tickets_cleaned.shape[1]),
        "reporting_eligible_rows": int(tickets_cleaned["reporting_eligible_flag"].sum()),
        "category_mismatch_rows": int(tickets_cleaned["category_mismatch_flag"].sum()),
        "sla_flag_mismatch_rows": int(tickets_cleaned["sla_flag_mismatch"].sum()),
        "public_holiday_ticket_rows": int(tickets_cleaned["is_public_holiday"].sum()),
        "outputs": [
            "tickets_cleaned.csv",
            "date_dimension.csv",
            "data_quality_summary.csv",
            "category_mapping.csv",
            "issue_taxonomy.csv",
        ],
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickets", type=Path, default=DEFAULT_TICKETS)
    parser.add_argument("--holidays", type=Path, default=DEFAULT_HOLIDAYS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = prepare(args.tickets, args.holidays, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
