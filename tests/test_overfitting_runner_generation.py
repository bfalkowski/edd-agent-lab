import json

from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.paths import LAB_RUNS_DIR


def test_overfitting_suite_writes_expected_metrics() -> None:
    result = run_eval_suite(
        agent_key="customer-solution",
        suite_id="overfitting",
        agent_version="v1-discovery-graph",
    )
    assert result.summary_path.is_file()
    payload = json.loads(result.summary_path.read_text(encoding="utf-8"))
    for field in [
        "base_case_passed",
        "variant_pass_rate",
        "behavioral_consistency_score",
        "overfitting_risk",
        "failed_variants",
        "variants",
    ]:
        assert field in payload

    assert isinstance(payload["failed_variants"], list)
    assert payload["overfitting_risk"] in {"high", "medium", "low", "unknown"}

    run_record = (
        LAB_RUNS_DIR / "customer_solution_agent" / "v1-discovery-graph" / "run-record.json"
    )
    assert run_record.is_file()
