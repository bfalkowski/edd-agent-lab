import json

from edd_agent_lab.integrations.edd_client import LocalEDDClient, QueuedEDDClient
from edd_agent_lab.integrations.publish import PUBLISH_SCHEMA_VERSION, build_publish_envelope
def test_build_publish_envelope_from_run_record() -> None:
    record = {
        "run_id": "2026-05-29T00-00-00Z",
        "agent": "customer_solution_agent",
        "agent_version": "v3-competency-model",
        "suite": "overfitting",
        "scenario_ids": ["healthcare_documentation"],
        "started_at": "2026-05-29T00-00-00Z",
        "completed_at": "2026-05-29T00-00-01Z",
        "outputs": {},
        "eval_summary": {"overall_score": 1.0},
        "failure_packet": None,
        "artifact_paths": {},
    }
    envelope = build_publish_envelope(record)
    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION
    assert envelope["source"] == "edd-agent-lab"
    assert envelope["agent_version"] == "v3-competency-model"
    assert envelope["eval_summary"]["overall_score"] == 1.0


def test_local_client_publish_envelope() -> None:
    client = LocalEDDClient()
    result = client.publish_envelope(
        {
            "schema_version": PUBLISH_SCHEMA_VERSION,
            "source": "edd-agent-lab",
            "run_id": "demo-run",
            "agent": "customer_solution_agent",
            "agent_version": "v1-discovery-graph",
            "suite": "discovery_quality",
            "scenario_ids": ["healthcare_documentation"],
            "eval_summary": {"overall_score": 0.9},
            "failure_packet": None,
            "outputs": {},
        }
    )
    assert result["status"] == "published_local"
    assert "platform_run_id" in result


def test_queued_client_writes_publish_file(tmp_path) -> None:
    client = QueuedEDDClient(queue_dir=tmp_path)
    envelope = {
        "schema_version": PUBLISH_SCHEMA_VERSION,
        "source": "edd-agent-lab",
        "run_id": "queued-run",
        "agent": "customer_solution_agent",
        "agent_version": "v1-discovery-graph",
        "suite": "overfitting",
        "scenario_ids": [],
        "eval_summary": {"overall_score": 0.4},
        "failure_packet": {"failure_type": "overfitting"},
        "outputs": {},
    }
    result = client.publish_envelope(envelope)
    assert result["status"] == "queued"
    queued_path = tmp_path / "queued-run.json"
    assert queued_path.is_file()
    payload = json.loads(queued_path.read_text(encoding="utf-8"))
    assert payload["suite"] == "overfitting"


def test_publish_from_run_record_dict(tmp_path) -> None:
    run_record = {
        "run_id": "2026-05-29T00-00-00Z",
        "agent": "customer_solution_agent",
        "agent_version": "v3-competency-model",
        "suite": "overfitting",
        "scenario_ids": ["healthcare_documentation"],
        "outputs": {},
        "eval_summary": {"overall_score": 1.0},
        "failure_packet": None,
        "artifact_paths": {},
    }
    client = QueuedEDDClient(queue_dir=tmp_path)
    result = client.publish_run_record(run_record)
    assert result["status"] == "queued"
