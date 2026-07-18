# Operations Runbook

## Local startup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python src/prepare_data.py
python scripts/build_duckdb.py
Copy-Item .env.example .env
streamlit run agent/app.py
```

Fake mode is the default. Use it for CI, offline demos, and dashboard review:

```powershell
$env:AGENT_LLM_MODE = "fake"
streamlit run agent/app.py
```

Live Groq mode must be explicit:

```powershell
$env:AGENT_LLM_MODE = "groq"
$env:GROQ_API_KEY = "your_real_key"
$env:GROQ_MODEL = "openai/gpt-oss-120b"
python scripts/run_agent.py "Which team had the lowest SLA compliance in 2024?"
```

Never commit a real API key. The audit log redacts common key patterns and email addresses, but `.env` remains ignored and should stay local.

## Docker startup

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8501`.

## Troubleshooting

- If the app says the DuckDB file is missing, run `python scripts/build_duckdb.py`.
- If Parquet is missing, run `python src/prepare_data.py`.
- If live Groq calls fail, check `AGENT_LLM_MODE`, `GROQ_API_KEY`, and `GROQ_MODEL`, then switch back to fake mode with `$env:AGENT_LLM_MODE = "fake"`.
- If a query is refused, check whether it asks for personal data, secrets, raw notes, file access, web access, or direct SQL.
- If SQL validation fails in Groq mode, the orchestrator retries once and records the failure reason in the trace.
