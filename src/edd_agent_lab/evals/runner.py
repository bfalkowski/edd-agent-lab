"""Eval suite execution for v0 baseline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_agent
from edd_agent_lab.evals.loading import load_eval_suite
from edd_agent_lab.evals.schemas import EvalSuite, OverfittingEvalSuite
from edd_agent_lab.evals.scoring import score_check, weighted_case_score
from edd_agent_lab.paths import LAB_RUNS_DIR


@dataclass
class EvalRunResult:
    run_id: str
    summary_path: Path
    failure_packet_path: Path | None
    summary: dict[str, object]


def run_eval_suite(
    agent_key: str,
    suite_id: str,
    agent_version: str = "v0-baseline",
) -> EvalRunResult:
    suite = load_eval_suite(agent_key=agent_key, suite_id=suite_id)
    if isinstance(suite, OverfittingEvalSuite):
        raise NotImplementedError("Overfitting suite execution lands in Milestone 5.")

    result = _run_standard_suite(
        agent_key=agent_key,
        suite=suite,
        agent_version=agent_version,
    )
    return result


def _run_standard_suite(agent_key: str, suite: EvalSuite, agent_version: str) -> EvalRunResult:
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_id = started_at
    case_summaries: list[dict[str, object]] = []

    for case in suite.cases:
        agent_result = run_customer_solution_agent(
            scenario_id=case.scenario,
            agent_key=agent_key,
            agent_version=agent_version,
        )
        check_scores = [score_check(check, agent_result.final_response) for check in case.checks]
        case_score = round(weighted_case_score(check_scores), 3)
        case_summaries.append(
            {
                "case_id": case.id,
                "scenario": case.scenario,
                "score": case_score,
                "checks": [item.as_dict() for item in check_scores],
                "run_artifact": str(agent_result.output_path),
            }
        )

    overall_score = round(sum(c["score"] for c in case_summaries) / len(case_summaries), 3)
    summary = {
        "agent": suite.agent,
        "agent_version": agent_version,
        "suite": suite.id,
        "run_id": run_id,
        "scenario_ids": [case["scenario"] for case in case_summaries],
        "started_at": started_at,
        "completed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
        "outputs": {
            case["scenario"]: {"run_artifact": case["run_artifact"]} for case in case_summaries
        },
        "overall_score": overall_score,
        "cases": case_summaries,
    }

    out_dir = LAB_RUNS_DIR / "customer_solution_agent" / agent_version
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_by_suite_path = out_dir / f"eval-summary-{suite.id}.json"
    summary_by_suite_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_path = out_dir / "eval-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    failed_checks = [
        check
        for case in case_summaries
        for check in case["checks"]
        if not bool(check["passed"])
    ]
    failure_packet_path = None
    if failed_checks:
        failure_packet = {
            "agent": suite.agent,
            "suite": suite.id,
            "run_id": run_id,
            "failure_type": "check_failures",
            "summary": f"{len(failed_checks)} checks failed in suite {suite.id}.",
            "evidence": {
                "overall_score": overall_score,
                "failed_checks": failed_checks,
            },
            "hypothesis": "Prompt and graph structure do not consistently satisfy eval criteria.",
            "recommended_fix": (
                "Implement one bounded behavior change and verify with the same eval suite."
            ),
        }
        failure_packet_by_suite_path = out_dir / f"failure-packet-{suite.id}.json"
        failure_packet_by_suite_path.write_text(
            json.dumps(failure_packet, indent=2), encoding="utf-8"
        )
        failure_packet_path = out_dir / "failure-packet.json"
        failure_packet_path.write_text(json.dumps(failure_packet, indent=2), encoding="utf-8")
    else:
        latest_failure = out_dir / "failure-packet.json"
        if latest_failure.is_file():
            latest_failure.unlink()

    run_record = {
        "run_id": run_id,
        "agent": suite.agent,
        "agent_version": agent_version,
        "suite": suite.id,
        "scenario_ids": summary["scenario_ids"],
        "started_at": started_at,
        "completed_at": summary["completed_at"],
        "outputs": summary["outputs"],
        "eval_summary": summary,
        "failure_packet": failure_packet if failed_checks else None,
        "artifact_paths": {
            "summary": str(summary_path),
            "summary_by_suite": str(summary_by_suite_path),
            "failure_packet": str(failure_packet_path) if failure_packet_path else None,
            "failure_packet_by_suite": (
                str(failure_packet_by_suite_path) if failed_checks else None
            ),
        },
    }
    run_record_path = out_dir / "run-record.json"
    run_record_path.write_text(json.dumps(run_record, indent=2), encoding="utf-8")

    return EvalRunResult(
        run_id=run_id,
        summary_path=summary_path,
        failure_packet_path=failure_packet_path,
        summary=summary,
    )
