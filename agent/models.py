"""Pydantic contracts shared by agent roles and tools."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisPlan(BaseModel):
    answerable: bool
    refusal_reason: str | None = None
    clarification_needed: bool = False
    clarification_question: str | None = None
    intent: Literal[
        "lookup",
        "aggregation",
        "comparison",
        "trend",
        "diagnosis",
        "data_quality",
        "definition",
    ]
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    time_range: str | None = None
    sort: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=200)
    required_tools: list[str] = Field(default_factory=list)
    caveat_topics: list[str] = Field(default_factory=list)
    expected_output: str = ""
    complexity: Literal["low", "medium", "high"] = "low"


class SQLCandidate(BaseModel):
    sql: str
    purpose: str
    tables_used: list[str]
    columns_used: list[str]
    metrics_used: list[str]
    expected_columns: list[str]
    detail_query: bool
    max_rows: int = Field(default=200, ge=1, le=200)


class EvidenceItem(BaseModel):
    claim: str
    value: str
    source_column_or_metric: str


class QueryResult(BaseModel):
    query_id: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    source_row_count: int
    execution_ms: int
    truncated: bool
    dataset_version: str
    sql_hash: str


class SQLValidationResult(BaseModel):
    approved: bool
    normalised_sql: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    estimated_complexity: Literal["low", "medium", "high"] = "low"
    reason: str | None = None


class FinalAnswerDraft(BaseModel):
    finding: str
    evidence: list[EvidenceItem]
    operational_interpretation: str
    recommended_action: str
    caveats: list[str]
    filters_applied: list[str]
    rows_analysed: int
    query_id: str
    dataset_version: str
    confidence: Literal["low", "medium", "high"]
    answer_markdown: str


class EvaluationResult(BaseModel):
    correctness: float = Field(ge=0, le=1)
    groundedness: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    safety: float = Field(ge=0, le=1)
    caveat_quality: float = Field(ge=0, le=1)
    actionability: float = Field(ge=0, le=1)
    cost_efficiency: float = Field(ge=0, le=1)
    hard_fail: bool
    issues: list[str]
    suggested_revision: str | None = None
    retry_required: bool

    @property
    def quality_score(self) -> float:
        return (
            0.25 * self.correctness
            + 0.20 * self.groundedness
            + 0.15 * self.completeness
            + 0.10 * self.relevance
            + 0.10 * self.safety
            + 0.08 * self.caveat_quality
            + 0.07 * self.actionability
            + 0.05 * self.cost_efficiency
        )


class UsageRecord(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class AgentResponse(BaseModel):
    state: str
    answer: FinalAnswerDraft | None = None
    evaluation: EvaluationResult | None = None
    plan: AnalysisPlan | None = None
    query_result: QueryResult | None = None
    sql: str | None = None
    refusal_reason: str | None = None
    usage: UsageRecord = Field(default_factory=UsageRecord)
    value_per_1k_tokens: float = 0.0
    value_per_usd: float = 0.0
