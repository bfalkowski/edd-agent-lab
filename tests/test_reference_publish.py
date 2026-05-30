from __future__ import annotations

import json
from pathlib import Path

from edd_agent_lab.integrations.publish import (
    PUBLISH_SCHEMA_VERSION,
    PUBLISH_SCHEMA_VERSION_V2,
    build_publish_envelope,
)
from edd_agent_lab.integrations.reference_publish import (
    enrich_escalation_run_record,
    load_reference_publish_artifacts,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "publish"


def test_load_reference_publish_artifacts_from_fixture() -> None:
    artifacts = load_reference_publish_artifacts()
    assert artifacts["failure_packet"]["id"] == "fp-v0-unsupported-root-cause"
    assert artifacts["fix_plan"]["id"] == "fix-v1-evidence-first-triage"
    assert len(artifacts["trace_links_v0"]) == 1
    assert len(artifacts["trace_links_v1"]) == 1


def test_enrich_escalation_run_record_v0() -> None:
    base = {
        "run_id": "test-v0",
        "agent": "customer_escalation_triage",
        "agent_version": "v0-baseline",
        "suite": "escalation_triage",
        "scenario_ids": ["escalation-latency-quality-regression-001"],
        "eval_summary": {"overall_score": 0.4},
        "failure_packet": {"failure_type": "check_failures", "summary": "generic"},
        "artifact_paths": {},
        "outputs": {},
    }
    enriched = enrich_escalation_run_record(base, agent_version="v0-baseline")

    assert enriched["agent"] == "customer_escalation_triage"
    assert enriched["agent_version"] == "v0-baseline"
    assert enriched["failure_packet"]["id"] == "fp-v0-unsupported-root-cause"
    assert enriched["trace_links"][0]["external_trace_id"] == "trace_v0_abc123"
    assert "publish_schema_version" not in enriched


def test_enrich_escalation_run_record_v1_builds_v2_publish_envelope() -> None:
    base = {
        "run_id": "test-v1",
        "agent": "customer_escalation_triage",
        "agent_version": "v1-evidence-triage-graph",
        "suite": "escalation_triage",
        "scenario_ids": ["escalation-latency-quality-regression-001"],
        "eval_summary": {"overall_score": 0.91},
        "failure_packet": None,
        "artifact_paths": {},
        "outputs": {},
    }
    enriched = enrich_escalation_run_record(base, agent_version="v1-evidence-triage-graph")
    envelope = build_publish_envelope(enriched)

    assert enriched["publish_schema_version"] == "2"
    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION_V2
    assert envelope["fix_plan"]["id"] == "fix-v1-evidence-first-triage"
    assert envelope["comparison"]["id"] == "compare-v0-v1-escalation-triage"
    assert envelope["gate_result"]["overall_status"] == "pass_for_demo_not_production"
    assert envelope["trace_links"][0]["external_trace_id"] == "trace_v1_def456"


def test_fixture_run_records_match_reference_publish() -> None:
    v0 = json.loads((FIXTURES_DIR / "evidence-run-record-v0-fail.json").read_text(encoding="utf-8"))
    v0_envelope = build_publish_envelope(v0)
    assert v0_envelope["schema_version"] == PUBLISH_SCHEMA_VERSION
    assert v0_envelope["failure_packet"]["id"] == "fp-v0-unsupported-root-cause"

    v1 = json.loads((FIXTURES_DIR / "evidence-run-record-v1-pass.json").read_text(encoding="utf-8"))
    v1_envelope = build_publish_envelope(v1)
    assert v1_envelope["schema_version"] == PUBLISH_SCHEMA_VERSION_V2
    assert v1_envelope["gate_result"]["overall_status"] == "pass_for_demo_not_production"
