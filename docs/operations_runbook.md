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

Replace `GROQ_API_KEY=MyAPI` in `.env` only if live Groq calls are needed. With the placeholder value, the app uses deterministic fake mode.

## Docker startup

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8501`.

## Troubleshooting

- If the app says the DuckDB file is missing, run `python scripts/build_duckdb.py`.
- If Parquet is missing, run `python src/prepare_data.py`.
- If live Groq calls fail, check `GROQ_API_KEY` and switch back to fake mode by restoring `GROQ_API_KEY=MyAPI`.
