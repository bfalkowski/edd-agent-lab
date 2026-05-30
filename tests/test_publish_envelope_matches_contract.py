from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from edd_agent_lab.integrations.publish import PUBLISH_SCHEMA_VERSION, build_publish_envelope

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "publish" / "v1"
ENVELOPE_KEYS = {
    "schema_version",
    "source",
    "run_id",
    "agent",
    "agent_version",
    "suite",
    "scenario_ids",
    "started_at",
    "completed_at",
    "outputs",
    "eval_summary",
    "failure_packet",
    "artifact_paths",
    "eval_spec_id",
}


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _fixture_to_run_record(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": fixture["run_id"],
        "agent": fixture["agent"],
        "agent_version": fixture["agent_version"],
        "suite": fixture["suite"],
        "scenario_ids": fixture.get("scenario_ids", []),
        "started_at": fixture.get("started_at"),
        "completed_at": fixture.get("completed_at"),
        "outputs": fixture.get("outputs", {}),
        "eval_summary": fixture.get("eval_summary"),
        "failure_packet": fixture.get("failure_packet"),
        "artifact_paths": fixture.get("artifact_paths", {}),
        "eval_spec_id": "00000000-0000-0000-0000-000000000001",
    }


@pytest.mark.parametrize(
    "fixture_name",
    [
        "envelope-pass.json",
        "envelope-fail-failure-packet.json",
        "envelope-insufficient-evidence.json",
    ],
)
def test_build_publish_envelope_matches_contract_fixture(fixture_name: str) -> None:
    fixture = _load_fixture(fixture_name)
    envelope = build_publish_envelope(_fixture_to_run_record(fixture))

    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION
    assert envelope["source"] == "edd-agent-lab"
    assert set(envelope.keys()) == ENVELOPE_KEYS

    for key in ENVELOPE_KEYS - {"eval_spec_id", "schema_version", "source"}:
        assert envelope[key] == fixture[key], f"mismatch for {key}"

    assert envelope["eval_spec_id"] == "00000000-0000-0000-0000-000000000001"
