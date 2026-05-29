"""Turn-level evaluation for side-by-side console."""

from __future__ import annotations

from edd_agent_lab.evals.loading import load_eval_suite
from edd_agent_lab.evals.schemas import EvalCheck
from edd_agent_lab.evals.scoring import score_check
from edd_agent_lab.evals.turn_schemas import TurnCheckResult, TurnEvaluation, TurnVersionResult

TURN_CHECK_IDS = (
    "asks_clarifying_questions",
    "identifies_workflow",
    "defines_success_metrics",
    "includes_risks",
    "proposes_eval_plan",
)

_TURN_CHECKS: list[EvalCheck] = [
    EvalCheck(
        id="asks_clarifying_questions",
        type="structure",
        weight=1.0,
        patterns=["discovery questions", "clarifying", "?"],
    ),
    EvalCheck(
        id="identifies_workflow",
        type="structure",
        weight=1.0,
        patterns=["workflow", "step", "handoff", "intake"],
    ),
    EvalCheck(
        id="defines_success_metrics",
        type="structure",
        weight=1.0,
        patterns=["success metrics", "measurement", "baseline", "kpi"],
    ),
    EvalCheck(
        id="includes_risks",
        type="structure",
        weight=1.0,
        patterns=["risk", "mitigation"],
    ),
    EvalCheck(
        id="proposes_eval_plan",
        type="structure",
        weight=1.0,
        patterns=["evaluation plan", "eval plan", "verification"],
    ),
]


def _fix_hint_for_check(check_id: str) -> str:
    hints = {
        "asks_clarifying_questions": (
            "Add explicit clarifying discovery questions before solutioning."
        ),
        "identifies_workflow": "Decompose the target workflow and handoffs.",
        "defines_success_metrics": "Define measurable success metrics with baselines.",
        "includes_risks": "List material risks and mitigations.",
        "proposes_eval_plan": "Include an evaluation and verification plan for the pilot.",
    }
    return hints.get(check_id, "Strengthen discovery discipline for this turn.")


def _evidence_for_check(check_id: str, response_text: str) -> list[str]:
    lowered = response_text.lower()
    evidence: list[str] = []
    for check in _TURN_CHECKS:
        if check.id != check_id:
            continue
        for pattern in check.patterns:
            if pattern in lowered:
                evidence.append(f"Found signal: '{pattern}'")
    if not evidence:
        evidence.append("Expected signals were not found in the response.")
    return evidence


def evaluate_turn(
    agent: str,
    scenario_id: str,
    suite_id: str,
    user_input: str,
    responses_by_version: dict[str, str],
) -> TurnEvaluation:
    _ = load_eval_suite(agent_key="customer-solution", suite_id=suite_id)

    version_results: list[TurnVersionResult] = []
    for agent_version, response_text in responses_by_version.items():
        check_results: list[TurnCheckResult] = []
        for check in _TURN_CHECKS:
            scored = score_check(check, response_text)
            check_results.append(
                TurnCheckResult(
                    id=check.id,
                    score=scored.score,
                    passed=scored.passed,
                    comment=scored.comment,
                    evidence=_evidence_for_check(check.id, response_text),
                    fix_hint=None if scored.passed else _fix_hint_for_check(check.id),
                )
            )
        overall = round(
            sum(item.score for item in check_results) / len(check_results),
            3,
        )
        version_results.append(
            TurnVersionResult(
                agent_version=agent_version,
                overall_score=overall,
                passed=all(item.passed for item in check_results),
                checks=check_results,
                strengths=[item.id for item in check_results if item.passed],
                gaps=[item.id for item in check_results if not item.passed],
            )
        )

    return TurnEvaluation(
        agent=agent,
        scenario_id=scenario_id,
        suite_id=suite_id,
        user_input=user_input,
        versions=version_results,
    )

