# Agent Architecture

The agent is a read-only structured-data analytics assistant for the prepared TechSolve support-ticket dataset.

## Runtime Modes

- `AGENT_LLM_MODE=auto` or `fake`: deterministic local agents for CI, offline demos, and Docker smoke tests.
- `AGENT_LLM_MODE=groq`: Groq-backed Planner, SQL Producer, Insight Producer, and Evaluator.

Live mode still keeps tool execution local. The model proposes structured plans, SQL candidates, insights, and evaluation results; Python validates every structure with Pydantic and approves SQL with local guardrails before DuckDB runs anything.

## Request Flow

```text
User question
  -> Input guard
  -> Planner
  -> SQL producer
  -> SQL AST guard
  -> Read-only DuckDB
  -> Insight producer
  -> Independent evaluator
  -> Bounded retry or final answer
  -> JSONL audit log
```

## Key Controls

- Input guard refuses personal data, secrets, prompt extraction, destructive SQL, filesystem access, web access, and arbitrary code requests before any LLM call.
- SQL guard allows one approved analytical statement and rejects DDL, DML, wildcard projections, unapproved tables/columns, external file functions, environment access, excessive joins, excessive CTEs, and deep subqueries.
- DuckDB runs with `read_only=True` and caps result rows/cells.
- Bounded retry uses `AGENT_MAX_RETRIES`, default `1`.
- Structured outputs are Pydantic validated for every Groq role.
- Audit traces include role type, prompt versions, retry count, generated SQL, validated SQL, query ID, dataset version, per-role usage, cost, value metrics, and stage latency.

## UI Layers

The manager view shows the grounded answer, evidence, full result table, chart, and provenance. The developer diagnostics panel is visible only when `AGENT_DEVELOPER_MODE=true` and shows plan, trace, evaluation, token usage, cost, and validated SQL without exposing hidden prompts.
