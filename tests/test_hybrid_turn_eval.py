from __future__ import annotations

from edd_agent_lab.evals.schemas import EvalCheck
from edd_agent_lab.evals.turn_evaluator import evaluate_turn, score_turn_check


def test_evaluate_turn_uses_structure_mode_in_mock() -> None:
    evaluation = evaluate_turn(
        agent="customer_solution_agent",
        scenario_id="healthcare_documentation",
        suite_id="discovery_quality",
        user_input="Reduce documentation burden",
        responses_by_version={
            "v1-discovery-graph": (
                "# Brief\n## Clarifying Discovery Questions\n?\n"
                "## Workflow\nworkflow handoff intake\n"
                "## Success Metrics\nsuccess metrics baseline measurement\n"
                "## Risks\nrisk mitigation\n## Evaluation Plan\neval plan verification\n"
            ),
        },
        generation_mode="mock",
    )
    assert evaluation.judge_mode == "structure"
    assert evaluation.versions[0].checks[0].method == "deterministic"


def test_score_turn_check_hybrid_combines_structure_and_llm(monkeypatch) -> None:
    from edd_agent_lab.evals.scoring import CheckScore

    def fake_score_check(check: EvalCheck, _text: str) -> CheckScore:
        return CheckScore(
            id=check.id,
            score=0.8,
            passed=True,
            comment="llm ok",
            weight=check.weight,
            method="llm_judge",
        )

    monkeypatch.setattr("edd_agent_lab.evals.turn_evaluator.score_check", fake_score_check)
    check = EvalCheck(
        id="asks_clarifying_questions",
        type="llm_judge",
        weight=1.0,
        rubric="Ask clarifying questions.",
        patterns=["discovery questions", "?"],
    )
    scored = score_turn_check(check, "discovery questions about workflow?", hybrid=True)
    assert scored.method == "hybrid"
    assert 0.0 < scored.score <= 1.0


def test_hybrid_turn_eval_when_live_and_api_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_GENERATION_MODE", "live")

    from edd_agent_lab.evals.scoring import CheckScore

    def fake_score_check(check: EvalCheck, response_text: str) -> CheckScore:
        return CheckScore(
            id=check.id,
            score=0.9,
            passed=True,
            comment="mock llm",
            weight=check.weight,
            method="llm_judge",
        )

    monkeypatch.setattr("edd_agent_lab.evals.turn_evaluator.score_check", fake_score_check)

    evaluation = evaluate_turn(
        agent="customer_solution_agent",
        scenario_id="healthcare_documentation",
        suite_id="discovery_quality",
        user_input="test",
        responses_by_version={"v1-discovery-graph": "discovery questions workflow ?"},
        generation_mode="live",
    )
    assert evaluation.judge_mode == "hybrid"
    assert any(check.method == "hybrid" for check in evaluation.versions[0].checks)
