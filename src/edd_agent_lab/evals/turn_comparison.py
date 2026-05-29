"""Compare turn-level evaluation results across agent versions."""

from __future__ import annotations

from edd_agent_lab.evals.turn_schemas import TurnComparison, TurnEvaluation


def _version_result(evaluation: TurnEvaluation, version: str):
    for item in evaluation.versions:
        if item.agent_version == version:
            return item
    raise ValueError(f"Version not found in evaluation: {version}")


def compare_turn_evaluation(
    evaluation: TurnEvaluation,
    before_version: str,
    after_version: str,
) -> TurnComparison:
    before = _version_result(evaluation, before_version)
    after = _version_result(evaluation, after_version)
    delta = round(after.overall_score - before.overall_score, 3)

    before_checks = {item.id: item.score for item in before.checks}
    after_checks = {item.id: item.score for item in after.checks}
    improved: list[str] = []
    regressed: list[str] = []
    unchanged: list[str] = []
    major_regression = False

    for check_id in sorted(set(before_checks) | set(after_checks)):
        b_score = before_checks.get(check_id, 0.0)
        a_score = after_checks.get(check_id, 0.0)
        change = a_score - b_score
        if change >= 0.05:
            improved.append(check_id)
        elif change <= -0.05:
            regressed.append(check_id)
            if change <= -0.20:
                major_regression = True
        else:
            unchanged.append(check_id)

    if before.overall_score == 0.0 and after.overall_score == 0.0:
        decision = "insufficient evidence"
        explanation = "Both versions scored at zero for this turn."
    elif delta >= 0.15 and not major_regression:
        decision = "after version is better for this turn"
        explanation = (
            f"{after_version} improved overall score by {delta:+.3f} "
            "without major regressions."
        )
    elif delta <= -0.10:
        decision = "after version regressed for this turn"
        explanation = f"{after_version} dropped overall score by {delta:+.3f}."
    elif abs(delta) < 0.05:
        decision = "no meaningful difference"
        explanation = f"Score delta {delta:+.3f} is within the no-change band."
    else:
        decision = "mixed result"
        explanation = (
            f"Score delta {delta:+.3f} with mixed check movement "
            f"(improved={len(improved)}, regressed={len(regressed)})."
        )

    return TurnComparison(
        before_version=before_version,
        after_version=after_version,
        before_score=before.overall_score,
        after_score=after.overall_score,
        score_delta=delta,
        decision=decision,
        improved_checks=improved,
        regressed_checks=regressed,
        unchanged_checks=unchanged,
        explanation=explanation,
    )
