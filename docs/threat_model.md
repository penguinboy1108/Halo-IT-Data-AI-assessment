# Threat Model

## Threats

- Prompt injection
- Dataset prompt injection
- SQL injection
- Filesystem access
- Secret exfiltration
- Personal-data disclosure
- Denial of wallet
- Denial of service
- Excessive query output
- Hallucinated metrics
- Unsupported causality
- Employee-performance misuse
- Dependency compromise
- Container escalation
- Log leakage

## Controls

- Input guard refuses high-risk requests before planning.
- SQL guard allows only single-statement read-only analytical SQL.
- Table and column allowlists exclude direct personal fields.
- `SELECT *`, file functions, extension loading, system tables, and mutation statements are rejected.
- DuckDB is opened with `read_only=True` at runtime.
- Result rows are bounded.
- Answers include provenance and caveats.
- Docker runs as a non-root user with dropped capabilities and read-only filesystem in Compose.
- `.env` is ignored and `.env.example` contains only a placeholder key.
