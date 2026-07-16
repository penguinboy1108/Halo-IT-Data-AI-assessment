# Model Card

## Intended use

Operational analytics questions about the synthetic TechSolve support-ticket dataset.

## Provider

Default live provider: GroqCloud.

Configured model: `openai/gpt-oss-120b`.

## Local mode

When `GROQ_API_KEY` is missing or set to `MyAPI`, the app uses a deterministic fake path for assessment demos and tests.

## Limitations

- The dataset is synthetic.
- Public holiday comparisons are observational and must not be treated as causal proof.
- Direct customer names, emails, billing contacts, and unrestricted resolution notes are not exposed.
- The fake path covers the approved demo question families; live Groq integration should be evaluated before public deployment.
