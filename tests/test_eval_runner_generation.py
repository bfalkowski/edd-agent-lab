import json

from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.paths import LAB_RUNS_DIR


def test_eval_runner_writes_summary_and_optional_failure_packet() -> None:
    result = run_eval_suite(agent_key="customer-solution", suite_id="baseline")
    assert result.summary_path.is_file()

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["suite"] == "baseline"
    assert "overall_score" in summary
    assert summary["cases"]

    if result.failure_packet_path is not None:
        packet = json.loads(result.failure_packet_path.read_text(encoding="utf-8"))
        assert packet["suite"] == "baseline"


def test_eval_runner_writes_version_specific_artifacts() -> None:
    run_eval_suite(agent_key="customer-solution", suite_id="discovery_quality", agent_version="v0-baseline")
    run_eval_suite(
        agent_key="customer-solution",
        suite_id="discovery_quality",
        agent_version="v1-discovery-graph",
    )
    v0_summary = (
        LAB_RUNS_DIR / "customer_solution_agent" / "v0-baseline" / "eval-summary-discovery_quality.json"
    )
    v1_summary = (
        LAB_RUNS_DIR
        / "customer_solution_agent"
        / "v1-discovery-graph"
        / "eval-summary-discovery_quality.json"
    )
    assert v0_summary.is_file()
    assert v1_summary.is_file()
