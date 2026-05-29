"""Scorecard helpers for eval suite summaries (console + CLI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edd_agent_lab.evals.runner import EvalRunResult


@dataclass(frozen=True)
class SuiteScorecardRow:
    item_id: str
    scenario: str
    score: float
    passed: bool
    detail: str


@dataclass(frozen=True)
class SuiteRunSnapshot:
    agent_version: str
    suite_id: str
    run_id: str
    overall_score: float
    passed: bool
    summary_path: str
    failure_packet_path: str | None
    rows: list[SuiteScorecardRow]
    summary: dict[str, Any]


def suite_scorecard_rows(summary: dict[str, Any]) -> list[SuiteScorecardRow]:
    """Flatten eval summary into table rows for the console scorecard."""
    if "cases" in summary:
        return [
            SuiteScorecardRow(
                item_id=str(case["case_id"]),
                scenario=str(case["scenario"]),
                score=float(case["score"]),
                passed=all(bool(check["passed"]) for check in case.get("checks", [])),
                detail=f"{sum(1 for c in case.get('checks', []) if c.get('passed'))}/"
                f"{len(case.get('checks', []))} checks",
            )
            for case in summary["cases"]
        ]

    rows: list[SuiteScorecardRow] = []
    base_case = summary.get("base_case")
    if isinstance(base_case, dict):
        rows.append(
            SuiteScorecardRow(
                item_id=str(base_case.get("id", "base_case")),
                scenario=str(base_case.get("scenario", "")),
                score=float(base_case.get("score", 0.0)),
                passed=bool(summary.get("base_case_passed", False)),
                detail="base case",
            )
        )
    for variant in summary.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        rows.append(
            SuiteScorecardRow(
                item_id=str(variant.get("id", variant.get("scenario", "variant"))),
                scenario=str(variant.get("scenario", "")),
                score=float(variant.get("score", 0.0)),
                passed=bool(variant.get("passed", False)),
                detail=str(variant.get("mutation_type", "variant")),
            )
        )
    return rows


def snapshot_from_eval_result(result: EvalRunResult, suite_id: str) -> SuiteRunSnapshot:
    summary = result.summary
    rows = suite_scorecard_rows(summary)
    passed = result.failure_packet_path is None
    return SuiteRunSnapshot(
        agent_version=str(summary.get("agent_version", "")),
        suite_id=suite_id,
        run_id=result.run_id,
        overall_score=float(summary.get("overall_score", 0.0)),
        passed=passed,
        summary_path=str(result.summary_path),
        failure_packet_path=(
            str(result.failure_packet_path) if result.failure_packet_path else None
        ),
        rows=rows,
        summary=summary,
    )
