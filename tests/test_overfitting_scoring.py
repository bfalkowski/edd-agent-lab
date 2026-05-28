from edd_agent_lab.evals.overfitting import overfitting_risk


def test_high_overfitting_when_base_passes_and_variants_fail() -> None:
    assert overfitting_risk(base_case_passed=True, variant_pass_rate=0.2) == "high"


def test_low_overfitting_when_base_and_variants_pass() -> None:
    assert overfitting_risk(base_case_passed=True, variant_pass_rate=0.9) == "low"


def test_no_overfitting_claim_when_base_fails() -> None:
    assert overfitting_risk(base_case_passed=False, variant_pass_rate=0.95) == "unknown"
