import pytest

from edd_agent_lab.evals.loading import list_eval_suite_ids, load_eval_suite
from edd_agent_lab.evals.schemas import EvalSuite, OverfittingEvalSuite


def test_list_eval_suites() -> None:
    ids = list_eval_suite_ids("customer-solution")
    assert "discovery_quality" in ids
    assert "overfitting" in ids
    assert len(ids) >= 6


def test_load_discovery_quality_suite() -> None:
    suite = load_eval_suite("customer-solution", "discovery_quality")
    assert isinstance(suite, EvalSuite)
    assert suite.id == "discovery_quality"
    assert suite.agent == "customer_solution_agent"
    assert len(suite.cases) >= 1
    case = suite.cases[0]
    assert case.scenario == "healthcare_documentation"
    assert len(case.checks) == 4
    assert sum(c.weight for c in case.checks) == pytest.approx(1.0)


def test_load_overfitting_suite() -> None:
    suite = load_eval_suite("customer-solution", "overfitting")
    assert isinstance(suite, OverfittingEvalSuite)
    assert suite.base_case.scenario == "healthcare_documentation"
    assert len(suite.variants) >= 4
    assert {v.mutation_type for v in suite.variants} == {"domain_swap"}


def test_missing_eval_suite_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_eval_suite("customer-solution", "missing_suite")
