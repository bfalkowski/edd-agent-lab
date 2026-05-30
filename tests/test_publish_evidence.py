from __future__ import annotations

import json
from pathlib import Path

from edd_agent_lab.integrations.publish import (
    PUBLISH_SCHEMA_VERSION,
    PUBLISH_SCHEMA_VERSION_V2,
    build_publish_envelope,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "publish"


def _load_run_record(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_build_publish_envelope_includes_structured_failure_packet() -> None:
    record = _load_run_record("evidence-run-record-v0-fail.json")
    envelope = build_publish_envelope(record)

    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION
    assert envelope["failure_packet"]["id"] == "fp-v0-unsupported-root-cause"
    assert envelope["failure_packet"]["failed_rule"] == "separate_facts_from_hypotheses"


def test_build_publish_envelope_v2_includes_evidence_bundle() -> None:
    record = _load_run_record("evidence-run-record-v1-pass.json")
    envelope = build_publish_envelope(record)

    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION_V2
    assert envelope["fix_plan"]["id"] == "fix-v1-evidence-first-triage"
    assert envelope["comparison"]["id"] == "compare-v0-v1-escalation-triage"
    assert envelope["gate_result"]["overall_status"] == "pass_for_demo_not_production"
