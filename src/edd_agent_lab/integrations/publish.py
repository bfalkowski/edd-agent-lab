"""Build platform-compatible publish envelopes from local lab run records."""

from __future__ import annotations

import os
from typing import Any

from edd_agent_lab.integrations.evidence import attach_evidence_to_envelope

PUBLISH_SCHEMA_VERSION = "1"
PUBLISH_SCHEMA_VERSION_V2 = "2"


def build_publish_envelope(
    run_record: dict[str, Any],
    *,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """Normalize a local run-record.json into a lab publish envelope."""
    version = schema_version or run_record.get("publish_schema_version") or PUBLISH_SCHEMA_VERSION
    if version == PUBLISH_SCHEMA_VERSION_V2:
        return _build_v2_envelope(run_record)
    return _build_v1_envelope(run_record)


def _build_v1_envelope(run_record: dict[str, Any]) -> dict[str, Any]:
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
    if run_record.get("tool_mode_summary"):
        envelope["tool_mode_summary"] = run_record["tool_mode_summary"]
    if "production_ready" in run_record:
        envelope["production_ready"] = run_record["production_ready"]
    if run_record.get("tool_bindings"):
        envelope["tool_bindings"] = run_record["tool_bindings"]
    if run_record.get("idempotency_key"):
        envelope["idempotency_key"] = run_record["idempotency_key"]
    return attach_evidence_to_envelope(envelope, run_record)


def _build_v2_envelope(run_record: dict[str, Any]) -> dict[str, Any]:
    tool_context = dict(run_record.get("tool_context") or {})
    if run_record.get("tool_bindings") and "tool_bindings" not in tool_context:
        tool_context["tool_bindings"] = run_record["tool_bindings"]
    if run_record.get("tool_mode_summary") and "tool_mode_summary" not in tool_context:
        tool_context["tool_mode_summary"] = run_record["tool_mode_summary"]
    if "production_ready" in run_record and "production_ready" not in tool_context:
        tool_context["production_ready"] = run_record["production_ready"]

    producer = dict(
        run_record.get("producer")
        or {
            "name": "edd-agent-lab",
            "environment": run_record.get("environment", "local_demo"),
            "run_mode": tool_context.get("tool_mode_summary", "mock_local"),
        }
    )

    agent = run_record.get("agent")
    agent_version = run_record.get("agent_version")
    if isinstance(agent, str):
        agent_payload: str | dict[str, Any] = {
            "id": agent,
            "name": run_record.get("agent_name", agent),
        }
    else:
        agent_payload = agent or {
            "id": run_record.get("agent_id", "unknown-agent"),
            "name": run_record.get("agent_name", "Unknown Agent"),
        }

    if isinstance(agent_version, str):
        agent_version_payload: str | dict[str, Any] = {
            "id": agent_version,
            "version_label": agent_version,
            "agent_id": agent_payload["id"] if isinstance(agent_payload, dict) else agent,
        }
    else:
        agent_version_payload = agent_version or {
            "id": run_record.get("agent_version_id", "unknown-version"),
            "version_label": run_record.get("agent_version_label", "unknown-version"),
        }

    envelope: dict[str, Any] = {
        "schema_version": PUBLISH_SCHEMA_VERSION_V2,
        "source": "edd-agent-lab",
        "run_id": run_record["run_id"],
        "producer": producer,
        "agent": agent_payload,
        "agent_version": agent_version_payload,
        "suite": run_record["suite"],
        "scenario_ids": run_record.get("scenario_ids", []),
        "tool_context": tool_context,
        "run": {
            "id": run_record["run_id"],
            "started_at": run_record.get("started_at"),
            "completed_at": run_record.get("completed_at"),
            "environment": producer.get("environment", "local_demo"),
        },
        "outputs": run_record.get("outputs", {}),
        "eval_summary": run_record.get("eval_summary"),
        "failure_packet": run_record.get("failure_packet"),
        "artifact_paths": run_record.get("artifact_paths", {}),
    }

    if run_record.get("target"):
        envelope["target"] = run_record["target"]
    if run_record.get("eval_contract"):
        envelope["eval_contract"] = run_record["eval_contract"]
    if run_record.get("scenario_set"):
        envelope["scenario_set"] = run_record["scenario_set"]
    if run_record.get("idempotency_key"):
        envelope["idempotency_key"] = run_record["idempotency_key"]

    eval_spec_id = run_record.get("eval_spec_id") or os.environ.get("EDD_EVAL_SPEC_ID")
    if eval_spec_id:
        envelope["eval_spec_id"] = eval_spec_id
    return attach_evidence_to_envelope(envelope, run_record)
