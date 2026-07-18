"""AST-based SQL policy validation."""

from __future__ import annotations

import re
from typing import Literal

import sqlglot
from sqlglot import exp

from agent.models import SQLValidationResult
from agent.settings import Settings, get_settings
from agent.tools.config_loader import load_yaml
from agent.tools.schema_tool import approved_column_names, approved_tables_and_columns

FORBIDDEN_NODE_TYPES = (
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Update,
    exp.Create,
    exp.Alter,
    exp.Command,
)


def _max_subquery_depth(node: exp.Expression, depth: int = 0) -> int:
    next_depth = depth + 1 if isinstance(node, exp.Subquery) else depth
    child_depths = [_max_subquery_depth(child, next_depth) for child in node.iter_expressions()]
    return max([next_depth, *child_depths])


def _keyword_pattern(words: list[str]) -> re.Pattern[str]:
    escaped = [re.escape(word) for word in words]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


def validate_sql(
    sql: str,
    *,
    detail_query: bool = False,
    settings: Settings | None = None,
) -> SQLValidationResult:
    settings = settings or get_settings()
    policy = load_yaml(settings.config_dir / "policy.yaml")["sql"]
    forbidden_keywords = _keyword_pattern([str(word) for word in policy["forbidden_keywords"]])
    forbidden_functions = {str(name).lower() for name in policy["forbidden_functions"]}

    risk_flags: list[str] = []
    stripped = sql.strip()
    if not stripped:
        return SQLValidationResult(approved=False, reason="SQL is empty")
    if forbidden_keywords.search(stripped):
        return SQLValidationResult(
            approved=False, reason="SQL contains a forbidden statement keyword"
        )
    if stripped.count(";") > 1 or (stripped.endswith(";") and ";" in stripped[:-1]):
        return SQLValidationResult(approved=False, reason="Multiple SQL statements are not allowed")

    try:
        statements = sqlglot.parse(stripped, read="duckdb")
    except sqlglot.errors.ParseError as exc:
        return SQLValidationResult(approved=False, reason=f"SQL parse failed: {exc}")

    if len(statements) != 1:
        return SQLValidationResult(approved=False, reason="Exactly one SQL statement is allowed")

    tree = statements[0]
    if tree is None:
        return SQLValidationResult(approved=False, reason="SQL parse returned an empty statement")
    first_token = stripped.split(None, 1)[0].upper()
    if first_token not in policy["allowed_statement_roots"]:
        return SQLValidationResult(
            approved=False, reason=f"{first_token} statements are not allowed"
        )

    if any(isinstance(node, FORBIDDEN_NODE_TYPES) for node in tree.walk()):
        return SQLValidationResult(approved=False, reason="SQL contains a forbidden AST node")

    for star in tree.find_all(exp.Star):
        if not isinstance(star.parent, exp.Count):
            return SQLValidationResult(
                approved=False, reason="Wildcard projections are not allowed"
            )

    tables, columns_by_table = approved_tables_and_columns(settings)
    global_columns = approved_column_names(settings)
    projection_aliases = {alias.alias for alias in tree.find_all(exp.Alias) if alias.alias}

    for table in tree.find_all(exp.Table):
        table_name = table.name
        if table_name.lower().startswith("information_schema") or table_name.lower().startswith(
            "duckdb_"
        ):
            return SQLValidationResult(approved=False, reason="System tables are not allowed")
        if table_name not in tables:
            return SQLValidationResult(
                approved=False, reason=f"Table is not approved: {table_name}"
            )

    for func in tree.find_all(exp.Func):
        function_name = func.sql_name().lower()  # type: ignore[no-untyped-call]
        if function_name in forbidden_functions:
            return SQLValidationResult(
                approved=False, reason=f"Function is not approved: {function_name}"
            )
    lowered = stripped.lower()
    if any(f"{name}(" in lowered for name in forbidden_functions):
        return SQLValidationResult(
            approved=False, reason="File, network, or extension function is not allowed"
        )

    for column in tree.find_all(exp.Column):
        column_name = column.name
        table_name = column.table
        if table_name:
            if table_name not in columns_by_table:
                return SQLValidationResult(
                    approved=False, reason=f"Column table is not approved: {table_name}"
                )
            if column_name not in columns_by_table[table_name]:
                return SQLValidationResult(
                    approved=False, reason=f"Column is not approved: {table_name}.{column_name}"
                )
        elif column_name not in global_columns and column_name not in projection_aliases:
            return SQLValidationResult(
                approved=False, reason=f"Column is not approved: {column_name}"
            )

    if detail_query and not tree.find(exp.Limit):
        return SQLValidationResult(
            approved=False, reason="Detail queries must include an explicit LIMIT"
        )

    join_count = len(list(tree.find_all(exp.Join)))
    cte_count = len(list(tree.find_all(exp.CTE)))
    subquery_depth = _max_subquery_depth(tree)
    if join_count > int(policy.get("max_joins", 4)):
        return SQLValidationResult(approved=False, reason="SQL exceeds maximum join count")
    if cte_count > int(policy.get("max_ctes", 4)):
        return SQLValidationResult(approved=False, reason="SQL exceeds maximum CTE count")
    if subquery_depth > int(policy.get("max_subquery_depth", 3)):
        return SQLValidationResult(approved=False, reason="SQL exceeds maximum subquery depth")
    if join_count > 3:
        risk_flags.append("many_joins")

    complexity: Literal["low", "medium", "high"] = "medium" if risk_flags else "low"
    return SQLValidationResult(
        approved=True,
        normalised_sql=tree.sql(dialect="duckdb"),
        risk_flags=risk_flags,
        estimated_complexity=complexity,
    )
