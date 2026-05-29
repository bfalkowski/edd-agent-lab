from edd_agent_lab.agents.customer_solution_agent.chat_responses import is_brief_response
from edd_agent_lab.agents.customer_solution_agent.runner import (
    build_user_problem,
    run_customer_solution_agent,
)
from edd_agent_lab.scenarios.loading import load_scenario


def test_console_chat_mode_returns_conversational_reply() -> None:
    result = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
        user_message="Clinicians spend 2 hours nightly on notes.",
        response_mode="chat",
        write_artifacts=False,
    )
    assert not is_brief_response(result.final_response)
    lowered = result.final_response.lower()
    assert "clinicians spend" in lowered or "clinician" in lowered
    assert "?" in result.final_response or "clarifying" in lowered


def test_followup_chat_differs_from_first_turn() -> None:
    history = [
        {"role": "user", "content": "Documentation takes too long."},
        {"role": "assistant", "content": "Let me ask a few clarifying questions first."},
    ]
    first = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
        user_message="Documentation takes too long.",
        response_mode="chat",
        write_artifacts=False,
    )
    followup = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
        user_message="What success metrics should we track?",
        conversation_history=history,
        response_mode="chat",
        write_artifacts=False,
    )
    assert not is_brief_response(followup.final_response)
    assert "metric" in followup.final_response.lower()
    assert followup.final_response != first.final_response


def test_brief_mode_still_returns_discovery_brief() -> None:
    result = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
        user_message="Documentation takes too long.",
        response_mode="brief",
        write_artifacts=False,
    )
    assert is_brief_response(result.final_response)


def test_v0_and_v1_chat_responses_differ_on_same_turn() -> None:
    msg = "Clinicians spend 2 hours nightly on documentation."
    v0 = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v0-baseline",
        user_message=msg,
        response_mode="chat",
        write_artifacts=False,
    )
    v1 = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
        user_message=msg,
        response_mode="chat",
        write_artifacts=False,
    )
    assert not is_brief_response(v0.final_response)
    assert not is_brief_response(v1.final_response)
    assert v0.final_response != v1.final_response


def test_v0_and_v1_followup_metrics_responses_differ() -> None:
    msg = "Clinicians spend 2 hours nightly on documentation."
    history_v0 = [
        {"role": "user", "content": msg},
        {"role": "assistant", "content": "v0 first turn placeholder"},
    ]
    history_v1 = [
        {"role": "user", "content": msg},
        {"role": "assistant", "content": "v1 first turn placeholder"},
    ]
    followup = "What success metrics should we track?"
    v0 = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v0-baseline",
        user_message=followup,
        conversation_history=history_v0,
        response_mode="chat",
        write_artifacts=False,
    )
    v1 = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
        user_message=followup,
        conversation_history=history_v1,
        response_mode="chat",
        write_artifacts=False,
    )
    assert not is_brief_response(v0.final_response)
    assert not is_brief_response(v1.final_response)
    assert v0.final_response != v1.final_response
    assert "pilot" in v0.final_response.lower() or "pragmatic" in v0.final_response.lower()
    assert "discovery" in v1.final_response.lower() or "clarity" in v1.final_response.lower()


def test_build_user_problem_includes_conversation_history() -> None:
    scenario = load_scenario("customer-solution", "healthcare_documentation")
    text = build_user_problem(
        scenario,
        user_message="What metrics should we track?",
        conversation_history=[
            {"role": "user", "content": "We need less documentation burden."},
            {"role": "assistant", "content": "Let us clarify workflow scope first."},
        ],
    )
    assert "Conversation so far:" in text
    assert "What metrics should we track?" in text
