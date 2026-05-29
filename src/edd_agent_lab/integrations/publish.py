"""Build platform-compatible publish envelopes from local lab run records."""

from __future__ import annotations

import os
from typing import Any

PUBLISH_SCHEMA_VERSION = "1"


def build_publish_envelope(run_record: dict[str, Any]) -> dict[str, Any]:
    """Normalize a local run-record.json into the lab publish envelope."""
    envelope: dict[str, Any] = {
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
    eval_spec_id = run_record.get("eval_spec_id") or os.environ.get("EDD_EVAL_SPEC_ID")
    if eval_spec_id:
        envelope["eval_spec_id"] = eval_spec_id
    return envelope
