# Halo IT Data & AI Assessment

This repository contains the practical assessment deliverables for the Halo IT
Data & AI Specialist scenario: prepared data, a Power BI dashboard, and a
Docker-ready AI analytics agent.

## Assessment Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| Part 1: Source, Combine & Prepare | Complete | `src/prepare_data.py`, `data/processed/*`, `docs/part1_data_preparation.md` |
| External data source | Complete | NZ national public holidays in `data/raw/nz_public_holidays.csv`; optional refresh via `src/fetch_public_holidays.py` |
| Consistent categories and sub-categories | Complete | `reporting_category`, `reporting_subcategory`, `category_mapping.csv`, `issue_taxonomy.csv` |
| Part 2: Visualise | Complete artifact | `power_bi/Dashboard.pbix` |
| Part 3: AI Agent | Complete | Streamlit + DuckDB agent under `agent/`, Dockerfile, `docker-compose.yml` |
| Required written review | Complete | `docs/assessment_review_response.md` |

Final manual check before submission: open `power_bi/Dashboard.pbix` in Power BI
Desktop and confirm the visual pages render as intended after refresh. The PBIX
binary is committed, but its internal visual layout is not inspected by the
Python test suite.

## AI Agent

The repository now includes a Docker-ready, read-only operational analytics agent.

The agent uses:

- Streamlit UI
- DuckDB over `data/processed/tickets_cleaned.parquet`
- strict SQL validation with `sqlglot`
- table and column allowlists
- `structlog`-backed JSONL audit logging for every agent request, including generated SQL
- business-focused answer drafting with evidence, possible drivers, recommendations, caveats, and provenance
- Streamlit result tables and automatic pandas-backed charts from the executed DuckDB query result
- deterministic fake LLM mode for local testing and CI
- explicit GroqCloud live mode through `AGENT_LLM_MODE=groq`
- Pydantic-validated Groq Planner, SQL Producer, Insight Producer, and Evaluator in live mode
- bounded retry, per-role token usage, cost estimates, value metrics, prompt versions, and stage latency traces

Run locally:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python src/prepare_data.py
python scripts/build_duckdb.py
Copy-Item .env.example .env
streamlit run agent/app.py
```

`.env.example` is safe to commit and defaults to fake mode. Fake mode is also
the default even if a local API key exists:

```powershell
$env:AGENT_LLM_MODE = "fake"
streamlit run agent/app.py
```

Live Groq mode must be enabled explicitly:

```powershell
$env:AGENT_LLM_MODE = "groq"
$env:GROQ_API_KEY = "your_real_key"
$env:GROQ_MODEL = "openai/gpt-oss-120b"
python scripts/build_duckdb.py
python scripts/run_agent.py "Which team had the lowest SLA compliance in 2024?"
```

Windows shortcut:

```powershell
scripts\start_agent.cmd
```

Background-style PowerShell launch:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_agent.ps1
```

Every request writes an audit record to:

```text
.runtime/agent_queries.jsonl
```

The log includes request IDs, redacted question text, generated SQL, validated SQL, query ID, evaluator score, retry count, prompt versions, per-role token/cost records, value metrics, result row/cell counts, and stage latency. `.runtime/` is ignored by Git.

The UI answer now shows:

- a grounded business finding and compact evidence table
- possible operational drivers to investigate, without claiming causality
- recommended management actions tied to the leading segment
- the full structured query result as a table
- an automatic chart: line chart for monthly trends and bar chart for team/category/holiday comparisons

Override the log path when needed:

```powershell
$env:AGENT_AUDIT_LOG_PATH = "D:\logs\halo_agent_queries.jsonl"
```

Run with Docker:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8501`.

`AGENT_LLM_MODE=auto` and `AGENT_LLM_MODE=fake` both use deterministic fake mode. Use `AGENT_LLM_MODE=groq` only for local live smoke tests; never commit a real key.

Agent checks:

```powershell
python src/prepare_data.py
python scripts/build_duckdb.py
ruff check .
ruff format --check .
mypy agent
pytest --cov=agent --cov-report=term-missing
python -m agent.evals.run --suite smoke
python -m agent.evals.run --suite security
bandit -r agent scripts
pip-audit
docker build --tag halo-it-agent:ci .
```

The CI workflow runs the preparation pipeline before linting, typing, tests, and
evals. The security workflow upgrades pip before installing the project, then
runs Bandit and pip-audit. Runtime dependencies explicitly include `openpyxl`
for reading the provided Excel workbook and `requests` for the optional NZ
public-holiday API refresh. Audited ranges pin `pyarrow` and `pytest` to versions
without the vulnerabilities reported by pip-audit at submission time.

For the full architecture and diagrams, see [design.md](design.md), [docs/agent_architecture.md](docs/agent_architecture.md), [docs/prompt_design.md](docs/prompt_design.md), and [docs/live_smoke_test.md](docs/live_smoke_test.md).

## Submission Checklist

- Prepared dataset: `data/processed/tickets_cleaned.csv` and `data/processed/tickets_cleaned.parquet`.
- Supporting model files: `date_dimension.csv`, `data_quality_summary.csv`, `category_mapping.csv`, and `issue_taxonomy.csv`.
- Dashboard: `power_bi/Dashboard.pbix`.
- AI agent access: run `docker compose up --build` and open `http://localhost:8501`.
- Written review: `docs/assessment_review_response.md`.
- Architecture and implementation notes: `design.md` and `docs/agent_architecture.md`.

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
- `data/processed/tickets_cleaned.parquet`
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

## Tests

```bash
python -m pytest
```

The tests cover the key deterministic transformation rules used by the data preparation pipeline.

## Security notes

- The runtime agent opens DuckDB in read-only mode.
- SQL is limited to a single approved analytical statement.
- Direct customer names, emails, billing contacts, and unrestricted resolution notes are not exposed.
- Personal-data, secret extraction, prompt extraction, destructive SQL, and filesystem access requests are refused before planning.
- Docker Compose runs with a read-only filesystem, no new privileges, and dropped Linux capabilities.
- Generated SQL and performance/provenance metadata are written to the JSONL audit log for every request.
