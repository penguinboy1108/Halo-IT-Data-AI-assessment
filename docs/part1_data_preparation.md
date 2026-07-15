# Part 1 Data Preparation Notes

## Requirement coverage

The assessment asks for the provided ticket dataset to be combined with at least one external data source and cleaned into reporting-ready categories and sub-categories. This implementation uses New Zealand national public holidays as the external data source because it can explain staffing, customer availability, backlog, and SLA variation around holidays.

## Source data profile

- Source workbook: `TechSolve - Ticket Data.xlsx`
- Rows: 100,851
- Columns: 36
- Main issue: the raw `category` field contains 32 label variants, while the issue descriptions map to a much smaller operational taxonomy.
- Date issues observed: out-of-period values in 1970 and 2099, a small number of resolved-before-created records, and resolved dates populated even for open-style statuses.

## Reporting taxonomy

The processed dataset keeps both source and derived issue labels:

- `source_category`: original category label from the workbook.
- `source_category_standard`: alias-cleaned source category.
- `source_reporting_category`: broader family inferred from the source category.
- `reporting_category`: issue family derived from `issue_description`.
- `reporting_subcategory`: more specific issue type derived from `issue_description`.
- `category_mismatch_flag`: true when source family and derived reporting family disagree.

Current reporting categories:

- Access & Security
- Billing & Payments
- Product Reliability
- Data & Integration
- Subscription Management
- Product Improvement

## Date and quality flags

The pipeline does not delete suspicious rows by default. It adds flags so downstream reporting can filter with intent:

- `plausible_created_date_flag`
- `reporting_period_flag`
- `resolution_before_creation_flag`
- `valid_resolved_date_flag`
- `status_date_consistency_flag`
- `open_status_with_resolution_flag`
- `reporting_eligible_flag`

For the 2024-2025 dashboard, use `reporting_eligible_flag = True` unless the data quality page is intentionally showing excluded records.

## Holiday enrichment

The date dimension and ticket dataset include:

- `is_public_holiday`
- `holiday_name`
- `is_day_before_holiday`
- `is_day_after_holiday`
- `holiday_period`
- `days_from_nearest_holiday`
- `nearest_holiday_name`

The first iteration uses national public holidays only. Regional anniversary days can be added later if we decide the extra complexity is worth it for regional analysis.
