"""Build platform-compatible publish envelopes from local lab run records."""

from __future__ import annotations

from typing import Any

PUBLISH_SCHEMA_VERSION = "1"


def build_publish_envelope(run_record: dict[str, Any]) -> dict[str, Any]:
    """Normalize a local run-record.json into the lab publish envelope."""
    return {
        "schema_version": PUBLISH_SCHEMA_VERSION,
        "source": "edd-agent-lab",
        "run_id": run_record["run_id"],
        "agent": run_record["agent"],
        "agent_version": run_record["agent_version"],
        "suite": run_record["suite"],
        "scenario_ids": run_record.get("scenario_ids", []),
        "started_at": run_record.get("started_at"),
        "completed_at": run_record.get("completed_at"),
        "outputs": run_record.get("outputs", {}),
        "eval_summary": run_record.get("eval_summary"),
        "failure_packet": run_record.get("failure_packet"),
        "artifact_paths": run_record.get("artifact_paths", {}),
    }
