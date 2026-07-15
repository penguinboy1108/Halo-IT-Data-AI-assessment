# Halo IT Data & AI Assessment

Part 1 is implemented as a reproducible data preparation pipeline.

## Part 1: Source, Combine & Prepare

Inputs:

- `data/raw/TechSolve - Ticket Data.xlsx` - provided synthetic ticket export.
- `data/raw/nz_public_holidays.csv` - national New Zealand public holidays for 2023-2025.
- Optional refresh source: `https://www.public-holidays.nz/docs.asp` via `src/fetch_public_holidays.py`.

Run:

```bash
python src/prepare_data.py
```

Outputs:

- `data/processed/tickets_cleaned.csv`
- `data/processed/date_dimension.csv`
- `data/processed/data_quality_summary.csv`
- `data/processed/category_mapping.csv`
- `data/processed/issue_taxonomy.csv`
- `data/processed/run_summary.json`

Latest run summary:

- Source rows: 100,851
- Cleaned rows: 100,851
- Cleaned columns: 93
- Reporting-eligible rows for 2024-2025: 67,136
- Category mismatch rows: 80,789
- SLA flag mismatch rows: 50,196
- Tickets created on national public holidays: 2,769

## Cleaning decisions

- Preserved raw ticket fields where useful and added explicit reporting fields instead of silently overwriting source values.
- Standardised 32 raw category labels into 10 canonical source categories.
- Derived a separate reporting category and sub-category from `issue_description`, because the source category is frequently inconsistent with the description.
- Added `category_mismatch_flag` so the dashboard can show how often the source label disagrees with the issue text.
- Added date quality flags for out-of-period dates, implausible dates, resolved-before-created records, and status/resolved-date inconsistencies.
- Added operational metrics for SLA variance, calculated SLA breach, breach severity, escalation, open/closed status, response/resolution buckets, customer value band, repeat-customer flag, and holiday windows.
- Removed direct customer name/email fields from the processed reporting dataset while keeping the raw file untouched.

## Public holiday API

The preferred external source is the public-holidays.nz API. It requires an API key:

```bash
set NZ_PUBLIC_HOLIDAYS_API_KEY=your_key_here
python src/fetch_public_holidays.py --years 2023 2024 2025
python src/prepare_data.py
```

The seeded `nz_public_holidays.csv` keeps the project runnable without an API key during assessment review.
