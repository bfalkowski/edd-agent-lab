from __future__ import annotations

from edd_agent_lab.integrations.reference_publish import load_reference_publish_artifacts
from edd_agent_lab.ui.demo_path import format_demo_summary, run_reference_demo_path
from edd_agent_lab.ui.reference_data import (
    comparison_metric_rows,
    load_mock_evidence_bundle,
    trace_link_rows,
)


def test_load_mock_evidence_bundle() -> None:
    bundle = load_mock_evidence_bundle()
    assert bundle["customer_report"]["customer"] == "Apex Health"
    assert bundle["tool_health"]["tools"]


def test_comparison_metric_rows_from_reference_artifacts() -> None:
    artifacts = load_reference_publish_artifacts()
    rows = comparison_metric_rows(artifacts)
    assert any(row["metric"] == "Diagnostic Grounding" for row in rows)
    assert rows[0]["delta"] is not None


def test_trace_link_rows_from_reference_artifacts() -> None:
    artifacts = load_reference_publish_artifacts()
    rows = trace_link_rows(artifacts)
    assert len(rows) == 2
    assert rows[0]["provider"] == "langfuse"


def test_run_reference_demo_path() -> None:
    result = run_reference_demo_path(publish=False)
    assert "## Facts" in result.v1_response
    assert "likely cause" in result.v0_response.lower()
    assert result.v0_snapshot.overall_score < result.v1_snapshot.overall_score
    assert not result.v0_passed
    assert result.v1_passed
    summary = format_demo_summary(result)
    assert "fp-v0-unsupported-root-cause" in summary
