from edd_agent_lab.agents.customer_solution_agent.state import CustomerSolutionState


def test_customer_solution_state_defaults() -> None:
    state = CustomerSolutionState(
        scenario_id="healthcare_documentation",
        user_problem="Need to reduce clinician documentation burden.",
    )
    assert state.scenario_id == "healthcare_documentation"
    assert state.discovery_questions == []
    assert state.success_metrics == []
    assert state.risks == []
    assert state.final_response is None
