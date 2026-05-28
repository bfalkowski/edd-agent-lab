"""Eval suite execution for v0 baseline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_agent
from edd_agent_lab.evals.loading import load_eval_suite
from edd_agent_lab.evals.overfitting import overfitting_risk
from edd_agent_lab.evals.schemas import EvalCheck, EvalSuite, OverfittingEvalSuite
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
        return _run_overfitting_suite(agent_key=agent_key, suite=suite, agent_version=agent_version)

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


def _run_overfitting_suite(
    agent_key: str, suite: OverfittingEvalSuite, agent_version: str
) -> EvalRunResult:
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_id = started_at
    out_dir = LAB_RUNS_DIR / "customer_solution_agent" / agent_version
    out_dir.mkdir(parents=True, exist_ok=True)

    base_result = run_customer_solution_agent(
        scenario_id=suite.base_case.scenario,
        agent_key=agent_key,
        agent_version=agent_version,
    )
    base_checks = [score_check(check, base_result.final_response) for check in suite.base_case.checks]
    base_score = round(weighted_case_score(base_checks), 3) if base_checks else 0.0
    base_passed = all(check.passed for check in base_checks) if base_checks else False

    variant_results: list[dict[str, object]] = []
    failed_variants: list[str] = []
    variant_scores: list[float] = []
    variant_check = EvalCheck(
        id="discovery_discipline_invariant",
        type="llm_judge",
        weight=1.0,
        rubric=(
            "Response preserves discovery-first behavior: identifies workflow, stakeholders, "
            "success metrics, risks, and an evaluation plan before overcommitting to solution details."
        ),
    )
    for variant in suite.variants:
        agent_result = run_customer_solution_agent(
            scenario_id=variant.scenario,
            agent_key=agent_key,
            agent_version=agent_version,
        )
        check = score_check(variant_check, agent_result.final_response)
        variant_scores.append(check.score)
        if not check.passed:
            failed_variants.append(variant.id)
        variant_results.append(
            {
                "id": variant.id,
                "scenario": variant.scenario,
                "mutation_type": variant.mutation_type,
                "expected_invariant": variant.expected_invariant,
                "score": check.score,
                "passed": check.passed,
                "comment": check.comment,
                "method": check.method,
                "run_artifact": str(agent_result.output_path),
            }
        )

    variant_pass_rate = round(
        (sum(1 for item in variant_results if bool(item["passed"])) / len(variant_results))
        if variant_results
        else 0.0,
        3,
    )
    behavioral_consistency_score = round(
        sum(variant_scores) / len(variant_scores) if variant_scores else 0.0,
        3,
    )
    risk = overfitting_risk(base_case_passed=base_passed, variant_pass_rate=variant_pass_rate)
    summary = {
        "agent": suite.agent,
        "agent_version": agent_version,
        "suite": suite.id,
        "run_id": run_id,
        "scenario_ids": [suite.base_case.scenario, *[v.scenario for v in suite.variants]],
        "started_at": started_at,
        "completed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
        "outputs": {
            suite.base_case.scenario: {"run_artifact": str(base_result.output_path)},
            **{item["scenario"]: {"run_artifact": item["run_artifact"]} for item in variant_results},
        },
        "base_case_passed": base_passed,
        "base_case_score": base_score,
        "variant_pass_rate": variant_pass_rate,
        "behavioral_consistency_score": behavioral_consistency_score,
        "overall_score": behavioral_consistency_score,
        "overfitting_risk": risk,
        "failed_variants": failed_variants,
        "base_case": {
            "id": suite.base_case.id,
            "scenario": suite.base_case.scenario,
            "score": base_score,
            "checks": [item.as_dict() for item in base_checks],
            "run_artifact": str(base_result.output_path),
        },
        "variants": variant_results,
    }

    summary_by_suite_path = out_dir / f"eval-summary-{suite.id}.json"
    summary_by_suite_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_path = out_dir / "eval-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    failure_packet_path = None
    if risk in {"high", "medium"} or not base_passed:
        failure_packet = {
            "agent": suite.agent,
            "suite": suite.id,
            "run_id": run_id,
            "failure_type": "overfitting",
            "summary": (
                "Base case and variant behavior indicate overfitting risk."
                if base_passed
                else "Base case failed; cannot claim robust generalization."
            ),
            "evidence": {
                "base_case_passed": base_passed,
                "variant_pass_rate": variant_pass_rate,
                "behavioral_consistency_score": behavioral_consistency_score,
                "failed_variants": failed_variants,
                "overfitting_risk": risk,
            },
            "hypothesis": (
                "Agent behavior is tuned to base scenario phrasing and does not transfer consistently."
            ),
            "recommended_fix": (
                "Introduce domain-neutral competency constraints and re-run overfitting suite."
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
        "failure_packet": (
            json.loads(failure_packet_path.read_text(encoding="utf-8"))
            if failure_packet_path
            else None
        ),
        "artifact_paths": {
            "summary": str(summary_path),
            "summary_by_suite": str(summary_by_suite_path),
            "failure_packet": str(failure_packet_path) if failure_packet_path else None,
            "failure_packet_by_suite": (
                str(out_dir / f"failure-packet-{suite.id}.json") if failure_packet_path else None
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
