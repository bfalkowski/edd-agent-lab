from edd_agent_lab.integrations.edd_client import LocalEDDClient


def test_local_edd_client_supports_stable_interface() -> None:
    client = LocalEDDClient()
    run_id = client.create_experiment_run(
        agent="customer_solution_agent",
        agent_version="v0-baseline",
        suite="discovery_quality",
        scenario_ids=["healthcare_documentation"],
    )
    assert run_id.startswith("local-")
    assert "customer_solution_agent" in run_id
    assert "v0-baseline" in run_id
    assert "discovery_quality" in run_id

    client.log_agent_output(
        run_id=run_id,
        scenario_id="healthcare_documentation",
        output={"final_response": "ok"},
        metadata={"source": "test"},
    )
    client.log_eval_summary(run_id=run_id, eval_summary={"overall_score": 0.8})
    client.log_failure_packet(run_id=run_id, failure_packet={"failure_type": "check_failures"})

    result = client.compare_runs(before_run_id=run_id, after_run_id=run_id)
    assert result["status"] == "local_stub"
    assert result["before_summary"] == {"overall_score": 0.8}


def test_local_edd_client_publish_envelope_roundtrip() -> None:
    client = LocalEDDClient()
    result = client.publish_envelope(
        {
            "schema_version": "1",
            "source": "edd-agent-lab",
            "run_id": "roundtrip-run",
            "agent": "customer_solution_agent",
            "agent_version": "v3-competency-model",
            "suite": "overfitting",
            "scenario_ids": ["healthcare_documentation"],
            "eval_summary": {"overall_score": 1.0},
            "failure_packet": None,
            "outputs": {},
        }
    )
    assert result["status"] == "published_local"
    compare = client.compare_runs(
        before_run_id=str(result["platform_run_id"]),
        after_run_id=str(result["platform_run_id"]),
    )
    assert compare["before_summary"]["overall_score"] == 1.0


def test_local_edd_client_compat_shims() -> None:
    client = LocalEDDClient()
    run_id = client.create_run(agent="customer_solution_agent", suite="baseline")
    client.log_eval_result(run_id=run_id, result={"overall_score": 1.0})
    client.create_failure_packet(run_id=run_id, packet={"failure_type": "none"})
    result = client.compare_runs(before_run_id=run_id, after_run_id=run_id)
    assert result["before_summary"] == {"overall_score": 1.0}
