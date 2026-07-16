# Agent Architecture

The agent is a read-only structured-data analytics assistant for the prepared TechSolve support-ticket dataset.

Flow:

1. Input guard rejects personal data, secret extraction, destructive SQL, filesystem access, and prompt injection.
2. Planner creates a bounded `AnalysisPlan`.
3. SQL producer creates one `SQLCandidate`.
4. `sqlglot` validates the SQL against statement, table, column, wildcard, function, and multi-statement policies.
5. DuckDB executes the query from a read-only connection.
6. Insight producer formats a grounded answer with evidence and provenance.
7. Evaluator scores safety and groundedness.

The current implementation uses a deterministic fake LLM path for local assessment, CI, and Docker smoke tests. A real Groq key can be supplied through `GROQ_API_KEY` for live model integration work.
