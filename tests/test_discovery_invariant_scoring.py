from edd_agent_lab.evals.scoring import discovery_theme_patterns, score_discovery_invariant
from edd_agent_lab.scenarios.loading import load_scenario


def test_discovery_theme_patterns_are_scenario_specific() -> None:
    legal = load_scenario("customer-solution", "legal_review")
    banking = load_scenario("customer-solution", "banking_fraud")
    legal_patterns = discovery_theme_patterns(legal)
    banking_patterns = discovery_theme_patterns(banking)
    assert "legal" in legal_patterns
    assert "banking" in banking_patterns
    assert legal_patterns != banking_patterns


def test_score_discovery_invariant_passes_rich_response() -> None:
    scenario = load_scenario("customer-solution", "legal_review")
    response = (
        "# Brief\n"
        "## Workflow\n"
        "legal workflow decomposition for contract matter intake review escalation approval\n"
        "## Stakeholders\n"
        "attorney partner associate knowledge management security privilege requirements\n"
        "## Success Metrics\n"
        "quality cycle metrics measurable baseline precision\n"
        "## Risks\n"
        "liability accuracy surface risks mitigation\n"
        "## Evaluation Plan\n"
        "evaluation plan pilot verification scope clarify\n"
    )
    score = score_discovery_invariant(scenario, response)
    assert score.passed
    assert score.method == "theme_invariant"
