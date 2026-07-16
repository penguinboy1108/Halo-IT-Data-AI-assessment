FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY agent ./agent
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels ".[dev]"

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    AGENT_AUDIT_LOG_PATH=/tmp/halo-agent-logs/agent_queries.jsonl \
    HOME=/tmp \
    XDG_CONFIG_HOME=/tmp/.config \
    XDG_CACHE_HOME=/tmp/.cache

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY agent ./agent
COPY scripts ./scripts
COPY data/processed ./data/processed
COPY docs ./docs

RUN python scripts/build_duckdb.py \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"

CMD ["streamlit", "run", "agent/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
