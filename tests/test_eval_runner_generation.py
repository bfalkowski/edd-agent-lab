import json

from edd_agent_lab.evals.runner import run_eval_suite


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
