# Processed Data Dictionary

## Main file

`data/processed/tickets_cleaned.csv`

## Source-preserving fields

- `source_category`: raw issue category from the workbook.
- `source_category_standard`: cleaned source category after alias mapping.
- `source_reporting_category`: broader reporting family inferred from the cleaned source category.
- `source_sla_breached`: raw SLA breach flag from the workbook.
- `source_sla_breached_flag`: boolean version of the raw SLA flag.

## Reporting taxonomy fields

- `reporting_category`: category derived from `issue_description` for dashboard and AI use.
- `reporting_subcategory`: lower-level issue type derived from `issue_description`.
- `category_mismatch_flag`: true when `source_reporting_category` and `reporting_category` disagree.

## Date and holiday fields

- `created_at`, `resolved_at`, `account_created_at`: parsed timestamp fields.
- `created_date`, `resolved_date`: date-only fields for modelling.
- `created_year`, `created_quarter`, `created_month`, `created_month_name`, `created_iso_week`, `created_day_of_week`, `created_hour`: calendar attributes from created date.
- `is_weekend`: true when the ticket was created on Saturday or Sunday.
- `is_public_holiday`: true when the created date matches the holiday dataset.
- `holiday_name`: public holiday name for matched dates.
- `holiday_period`: one of `Public holiday`, `Day before holiday`, `Day after holiday`, `Regular day`, or `Outside date dimension`.
- `days_from_nearest_holiday`: absolute day distance to the nearest public holiday.
- `nearest_holiday_name`: name of the nearest public holiday.

## Data quality fields

- `plausible_created_date_flag`: true when the created date is inside 2023-2025.
- `reporting_period_flag`: true when the created date is inside 2024-2025.
- `resolution_before_creation_flag`: true when resolved time is earlier than created time.
- `valid_resolved_date_flag`: false for resolved-before-created records.
- `status_date_consistency_flag`: checks whether open-style statuses have no resolved date and closed-style statuses do have one.
- `open_status_with_resolution_flag`: true when `Open`, `In Progress`, or `Pending Customer` has a resolved date.
- `reporting_eligible_flag`: recommended filter for the Part 2 dashboard.

## Operational metrics

- `calculated_sla_breached`: recomputed as `resolution_time_hours > sla_target_hours`.
- `sla_flag_mismatch`: true when the workbook SLA flag disagrees with the recomputed flag.
- `sla_variance_hours`: `resolution_time_hours - sla_target_hours`.
- `sla_breach_severity`: `Within SLA`, `Minor breach`, `Moderate breach`, `Major breach`, or `Severe breach`.
- `is_escalated`: boolean version of `escalated`.
- `is_open_ticket`: true for `Open`, `In Progress`, or `Pending Customer`.
- `is_closed_ticket`: true for `Closed` or `Resolved`.
- `resolution_time_bucket`: bucketed resolution time.
- `first_response_bucket`: bucketed first response time.
- `complexity_bucket`: Low, Medium, or High based on `issue_complexity_score`.
- `customer_value_band`: contract value band from `monthly_contract_value`.
- `repeat_customer_flag`: true when `previous_tickets > 0`.

## Privacy and completeness fields

- Direct customer name and email fields are excluded from `tickets_cleaned.csv`.
- `customer_email_domain`: email domain retained for high-level channel/customer-pattern analysis.
- `billing_contact_present_flag`: true when the source row included a billing contact email.
- `company_name_clean`, `industry_clean`, `account_manager_clean`, `team_clean`, `assigned_to_clean`, `browser_clean`, `operating_system_clean`, `resolution_notes_clean`: reporting-safe fill values for common missing fields.
