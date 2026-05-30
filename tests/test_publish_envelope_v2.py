from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from edd_agent_lab.integrations.publish import (
    PUBLISH_SCHEMA_VERSION,
    PUBLISH_SCHEMA_VERSION_V2,
    build_publish_envelope,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "publish" / "v2"


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _fixture_to_run_record(fixture: dict[str, Any]) -> dict[str, Any]:
    tool_context = fixture.get("tool_context") or {}
    agent = fixture.get("agent")
    agent_version = fixture.get("agent_version")
    return {
        "run_id": fixture["run_id"],
        "agent": agent["id"] if isinstance(agent, dict) else agent,
        "agent_name": agent.get("name") if isinstance(agent, dict) else None,
        "agent_version": (
            agent_version.get("version_label")
            if isinstance(agent_version, dict)
            else agent_version
        ),
        "suite": fixture["suite"],
        "scenario_ids": fixture.get("scenario_ids")
        or (fixture.get("scenario_set") or {}).get("scenario_ids", []),
        "started_at": (fixture.get("run") or {}).get("started_at"),
        "completed_at": (fixture.get("run") or {}).get("completed_at"),
        "outputs": fixture.get("outputs", {}),
        "eval_summary": fixture.get("eval_summary"),
        "failure_packet": fixture.get("failure_packet"),
        "artifact_paths": fixture.get("artifact_paths", {}),
        "producer": fixture.get("producer"),
        "target": fixture.get("target"),
        "eval_contract": fixture.get("eval_contract"),
        "tool_context": tool_context,
        "tool_mode_summary": tool_context.get("tool_mode_summary"),
        "production_ready": tool_context.get("production_ready"),
        "tool_bindings": tool_context.get("tool_bindings"),
        "publish_schema_version": "2",
        "eval_spec_id": "00000000-0000-0000-0000-000000000001",
    }


@pytest.mark.parametrize(
    "fixture_name",
    [
        "envelope-pass-demo-not-production.json",
        "envelope-fail-failure-packet.json",
    ],
)
def test_build_publish_envelope_v2_matches_contract_fixture(fixture_name: str) -> None:
    fixture = _load_fixture(fixture_name)
    envelope = build_publish_envelope(_fixture_to_run_record(fixture))

    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION_V2
    assert envelope["producer"]["name"] == "edd-agent-lab"
    if "tool_context" in fixture:
        expected_mode = fixture["tool_context"]["tool_mode_summary"]
        assert envelope["tool_context"]["tool_mode_summary"] == expected_mode
    if "run" in fixture:
        assert envelope["run"]["id"] == fixture["run_id"]
    assert envelope["eval_spec_id"] == "00000000-0000-0000-0000-000000000001"


def test_build_publish_envelope_defaults_to_v1() -> None:
    record = {
        "run_id": "demo-run",
        "agent": "customer_solution_agent",
        "agent_version": "v1-discovery-graph",
        "suite": "discovery_quality",
        "scenario_ids": [],
        "outputs": {},
        "eval_summary": {"overall_score": 0.9},
        "failure_packet": None,
        "artifact_paths": {},
    }
    envelope = build_publish_envelope(record)
    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION
