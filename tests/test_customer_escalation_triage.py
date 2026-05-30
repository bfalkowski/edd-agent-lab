from __future__ import annotations

from edd_agent_lab.agents.customer_escalation_triage.runner import run_customer_escalation_triage
from edd_agent_lab.agents.registry import normalize_agent_dir
from edd_agent_lab.evals.loading import load_eval_suite
from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.scenarios.loading import list_scenario_ids, load_scenario


def test_escalation_scenario_loads() -> None:
    scenario = load_scenario(
        "customer-escalation-triage",
        "escalation-latency-quality-regression-001",
    )
    assert scenario.id == "escalation-latency-quality-regression-001"
    assert "Apex Health" in scenario.problem


def test_escalation_v0_mock_response_claims_root_cause() -> None:
    result = run_customer_escalation_triage(
        scenario_id="escalation-latency-quality-regression-001",
        agent_version="v0-baseline",
    )
    assert "likely cause" in result.final_response.lower()
    assert result.agent == normalize_agent_dir("customer-escalation-triage")


def test_escalation_v1_mock_response_separates_facts() -> None:
    result = run_customer_escalation_triage(
        scenario_id="escalation-latency-quality-regression-001",
        agent_version="v1-evidence-triage-graph",
    )
    assert "## Facts" in result.final_response
    assert "## Hypotheses" in result.final_response
    assert "not confirmed" in result.final_response.lower()


def test_escalation_eval_suite_runs_for_v1() -> None:
    suite = load_eval_suite("customer-escalation-triage", "escalation_triage")
    assert suite.id == "escalation_triage"
    assert list_scenario_ids("customer-escalation-triage") == [
        "escalation-latency-quality-regression-001"
    ]

    result = run_eval_suite(
        agent_key="customer-escalation-triage",
        suite_id="escalation_triage",
        agent_version="v1-evidence-triage-graph",
    )
    assert result.summary["overall_score"] == 1.0
    assert result.failure_packet_path is None


def test_escalation_eval_suite_v0_enriches_run_record() -> None:
    result = run_eval_suite(
        agent_key="customer-escalation-triage",
        suite_id="escalation_triage",
        agent_version="v0-baseline",
    )
    assert result.failure_packet_path is not None
    import json

    run_record = json.loads(
        result.failure_packet_path.parent.joinpath("run-record.json").read_text(encoding="utf-8")
    )
    assert run_record["failure_packet"]["id"] == "fp-v0-unsupported-root-cause"
    assert run_record["trace_links"][0]["external_trace_id"] == "trace_v0_abc123"
    assert run_record.get("publish_schema_version") is None
