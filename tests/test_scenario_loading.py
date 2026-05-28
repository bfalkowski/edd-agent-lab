import pytest

from edd_agent_lab.scenarios.loading import list_scenario_ids, list_scenarios, load_scenario


def test_list_customer_solution_scenarios() -> None:
    ids = list_scenario_ids("customer-solution")
    assert "healthcare_documentation" in ids
    assert len(ids) >= 6


def test_load_healthcare_scenario() -> None:
    scenario = load_scenario("customer-solution", "healthcare_documentation")
    assert scenario.id == "healthcare_documentation"
    assert scenario.domain == "healthcare"
    assert scenario.problem.strip()
    assert len(scenario.expected_themes) >= 3


def test_list_scenarios_returns_models() -> None:
    scenarios = list_scenarios("customer_solution_agent")
    assert all(s.id for s in scenarios)


def test_missing_scenario_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_scenario("customer-solution", "nonexistent_scenario")
