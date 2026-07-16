import pandas as pd

from src.prepare_data import (
    CATEGORY_ALIAS,
    bucket_hours,
    classify_issue,
    clean_key,
    complexity_bucket,
    value_band,
)


def test_category_alias_mapping():
    assert CATEGORY_ALIAS["bug"] == "Bug Report"
    assert CATEGORY_ALIAS["perf issue"] == "Performance Issue"
    assert CATEGORY_ALIAS["sub cancellation"] == "Subscription Cancellation"


def test_issue_classification():
    category, subcategory = classify_issue(
        "Two-factor authentication codes are not being delivered to my phone."
    )
    assert category == "Access & Security"
    assert subcategory == "MFA Failure"


def test_issue_classification_billing_dispute():
    category, subcategory = classify_issue(
        "There seems to be a discrepancy in my billing statement for this month."
    )
    assert category == "Billing & Payments"
    assert subcategory == "Billing Dispute"


def test_bucket_hours():
    assert bucket_hours(2) == "0-4 hours"
    assert bucket_hours(25) == "1-3 days"
    assert bucket_hours(200) == "7+ days"


def test_bucket_hours_handles_missing_values():
    assert bucket_hours(pd.NA) == "Unknown"


def test_supporting_bucket_rules():
    assert clean_key(" Perf_Issue  ") == "perf issue"
    assert complexity_bucket(7) == "High"
    assert value_band(0) == "Free / zero value"
