from __future__ import annotations

from edd_agent_lab.integrations.reference_publish import load_reference_publish_artifacts
from edd_agent_lab.ui.reference_data import (
    graph_diff_rows,
    graph_flow_summary,
    load_graph_design_bundle,
    reference_overall_score,
)


def test_graph_design_bundles_load_from_lab_target() -> None:
    v0_design, v0_nodes = load_graph_design_bundle("v0")
    v1_design, v1_nodes = load_graph_design_bundle("v1")

    assert v0_design["id"] == "customer-escalation-triage-graph-v0"
    assert v1_design["id"] == "customer-escalation-triage-graph-v1"
    assert "single_pass_response" in graph_flow_summary(v0_design, v0_nodes)
    assert "separate_facts_hypotheses_unknowns" in {
        node["id"] for node in v1_nodes
    }


def test_graph_diff_rows_include_v1_only_nodes() -> None:
    _, v0_nodes = load_graph_design_bundle("v0")
    _, v1_nodes = load_graph_design_bundle("v1")
    added = {row["added_node"] for row in graph_diff_rows(v0_nodes, v1_nodes)}
    assert "normalize_evidence" in added
    assert "separate_facts_hypotheses_unknowns" in added


def test_reference_overall_score_from_comparison_fixture() -> None:
    artifacts = load_reference_publish_artifacts()
    v0 = reference_overall_score(artifacts, "v0")
    v1 = reference_overall_score(artifacts, "v1")
    assert v0 is not None and v1 is not None
    assert v1 > v0
