import json

from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_agent


def test_run_agent_writes_artifact() -> None:
    result = run_customer_solution_agent(scenario_id="healthcare_documentation")
    assert result.final_response.strip()
    assert result.output_path.is_file()

    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload["agent"] == "customer_solution_agent"
    assert payload["agent_version"] == "v0-baseline"
    assert payload["scenario"]["id"] == "healthcare_documentation"
    assert "proposed_solution" in payload["response"]
