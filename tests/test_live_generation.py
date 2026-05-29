import pytest

from edd_agent_lab.agents.customer_solution_agent.live_generation import LiveDiscoveryDraft
from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_agent
from edd_agent_lab.agents.customer_solution_agent.state import (
    DiscoveryQuestion,
    Risk,
    SuccessMetric,
)
from edd_agent_lab.agents.generation import resolve_generation_mode


def test_resolve_generation_mode_mock() -> None:
    assert resolve_generation_mode("mock") == "mock"


def test_resolve_generation_mode_auto_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert resolve_generation_mode("auto") == "mock"


def test_resolve_generation_mode_auto_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert resolve_generation_mode("auto") == "live"


def test_resolve_generation_mode_live_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        resolve_generation_mode("live")


def test_run_customer_solution_agent_live_path(monkeypatch: pytest.MonkeyPatch) -> None:
    draft = LiveDiscoveryDraft(
        problem_summary="Customer needs faster documentation workflow.",
        discovery_questions=[
            DiscoveryQuestion(
                question="Which documentation step is slowest?",
                reason="Find pilot scope.",
            )
        ],
        workflow_summary="Intake -> draft -> review -> sign-off.",
        stakeholders=["Clinicians", "Compliance"],
        assumptions=["Baseline metrics exist."],
        proposed_solution="Copilot for note drafting.",
        success_metrics=[
            SuccessMetric(
                metric="Cycle time",
                why_it_matters="Primary value.",
                how_to_measure="Median minutes per note.",
            )
        ],
        risks=[
            Risk(
                risk="Incorrect draft content.",
                mitigation="Human review on high-risk cases.",
            )
        ],
        pilot_plan="4-week pilot on one unit.",
        eval_plan="Run discovery_quality suite each iteration.",
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "edd_agent_lab.agents.customer_solution_agent.runner.generate_discovery_draft",
        lambda *args, **kwargs: draft,
    )
    monkeypatch.setattr(
        "edd_agent_lab.agents.customer_solution_agent.runner.generate_live_chat_response",
        lambda *args, **kwargs: (
            "Let's clarify workflow steps first. Success metrics should include cycle time "
            "and quality. Risks include incorrect drafts with human-review mitigation."
        ),
    )

    result = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
        user_message="Clinicians spend 2 hours nightly on notes.",
        response_mode="chat",
        generation_mode="live",
        write_artifacts=False,
    )
    assert result.generation_mode == "live"
    assert "workflow" in result.final_response.lower()
    assert "success metrics" in result.final_response.lower()
    assert result.state.proposed_solution == "Copilot for note drafting."


def test_run_customer_solution_agent_mock_path_by_default() -> None:
    result = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v0-baseline",
        user_message="Documentation takes too long.",
        response_mode="chat",
        write_artifacts=False,
    )
    assert result.generation_mode == "mock"
