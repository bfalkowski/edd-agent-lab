import json

from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_agent
from edd_agent_lab.paths import LAB_RUNS_DIR


def test_run_agent_writes_artifact() -> None:
    result = run_customer_solution_agent(scenario_id="healthcare_documentation")
    assert result.final_response.strip()
    assert result.output_path.is_file()

    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload["agent"] == "customer_solution_agent"
    assert payload["agent_version"] == "v0-baseline"
    assert payload["scenario"]["id"] == "healthcare_documentation"
    assert "proposed_solution" in payload["response"]
    latest_output = LAB_RUNS_DIR / "customer_solution_agent" / "v0-baseline" / "agent-output.json"
    assert latest_output.is_file()


def test_run_agent_v1_writes_to_v1_directory() -> None:
    v0 = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v0-baseline",
    )
    v1 = run_customer_solution_agent(
        scenario_id="healthcare_documentation",
        agent_version="v1-discovery-graph",
    )
    assert "v0-baseline" in str(v0.output_path)
    assert "v1-discovery-graph" in str(v1.output_path)
    v0_latest = LAB_RUNS_DIR / "customer_solution_agent" / "v0-baseline" / "agent-output.json"
    v1_latest = (
        LAB_RUNS_DIR / "customer_solution_agent" / "v1-discovery-graph" / "agent-output.json"
    )
    assert v0_latest.is_file()
    assert v1_latest.is_file()
