# Prompt Design

Prompts are versioned files under `agent/prompts/` and selected by `agent/config/prompts.yaml`.

Current production prompts:

- `planner_v1.md`
- `sql_producer_v1.md`
- `insight_producer_v1.md`
- `evaluator_v1.md`

The audit trace records the active prompt version for each role. Hidden system prompts are not displayed in the Streamlit developer panel and are not written to the audit log.

## Role Boundaries

- Planner returns only `AnalysisPlan`; it does not write SQL.
- SQL Producer returns only `SQLCandidate`; it does not execute SQL.
- Insight Producer receives only compact verified query results and provenance; it does not see full datasets.
- Evaluator scores the answer independently; it does not answer the user.

## Safety Rules

Prompts reinforce that the model may not request files, shell, Python execution, web access, arbitrary HTTP, personal data, secrets, hidden prompts, unrestricted notes, or destructive SQL. These rules are advisory for the model; enforcement happens in local Python guardrails.

## Promotion Process

Prompt edits should be reviewed like code:

1. Update the versioned prompt file or add a new version.
2. Update `agent/config/prompts.yaml`.
3. Run fake-mode tests and evals.
4. Run mocked Groq integration tests.
5. Run a local live smoke test outside CI when a real key is available.
