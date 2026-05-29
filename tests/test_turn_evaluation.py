from edd_agent_lab.evals.turn_comparison import compare_turn_evaluation
from edd_agent_lab.evals.turn_evaluator import evaluate_turn


def test_evaluate_turn_scores_versions() -> None:
    evaluation = evaluate_turn(
        agent="customer_solution_agent",
        scenario_id="healthcare_documentation",
        suite_id="discovery_quality",
        user_input="Reduce documentation burden",
        responses_by_version={
            "v0-baseline": (
                "# Brief\n## Workflow\nworkflow steps\n"
                "## Success Metrics\nmetrics\n## Risks\nrisk mitigation\n"
            ),
            "v1-discovery-graph": (
                "# Brief\n## Clarifying Discovery Questions\n?\n"
                "## Workflow\nworkflow handoff intake\n"
                "## Success Metrics\nsuccess metrics baseline measurement\n"
                "## Risks\nrisk mitigation\n## Evaluation Plan\neval plan verification\n"
            ),
        },
    )
    assert len(evaluation.versions) == 2
    scores = {item.agent_version: item.overall_score for item in evaluation.versions}
    assert scores["v1-discovery-graph"] >= scores["v0-baseline"]


def test_compare_turn_evaluation_detects_improvement() -> None:
    evaluation = evaluate_turn(
        agent="customer_solution_agent",
        scenario_id="healthcare_documentation",
        suite_id="discovery_quality",
        user_input="test",
        responses_by_version={
            "v0-baseline": "short",
            "v1-discovery-graph": (
                "discovery questions workflow success metrics risk mitigation "
                "evaluation plan verification pilot"
            ),
        },
    )
    comparison = compare_turn_evaluation(
        evaluation,
        before_version="v0-baseline",
        after_version="v1-discovery-graph",
    )
    assert comparison.before_version == "v0-baseline"
    assert comparison.after_version == "v1-discovery-graph"
    assert comparison.decision in {
        "after version is better for this turn",
        "mixed result",
        "no meaningful difference",
        "insufficient evidence",
        "after version regressed for this turn",
    }
