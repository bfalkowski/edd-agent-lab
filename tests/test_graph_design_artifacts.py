from __future__ import annotations

from pathlib import Path

import pytest
import yaml

LAB_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = LAB_ROOT / "lab-runs" / "customer_escalation_triage" / "target"


def _load_bundle(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    graph_design = payload["graph_design"]
    graph_nodes = payload.get("graph_nodes", [])
    assert isinstance(graph_design, dict)
    assert isinstance(graph_nodes, list)
    return graph_design, graph_nodes


@pytest.mark.parametrize(
    ("filename", "expected_id", "min_nodes"),
    [
        ("graph-design-v0.yaml", "customer-escalation-triage-graph-v0", 2),
        ("graph-design.yaml", "customer-escalation-triage-graph-v1", 10),
    ],
)
def test_graph_design_artifacts_validate(filename: str, expected_id: str, min_nodes: int) -> None:
    path = TARGET_DIR / filename
    assert path.is_file(), f"missing lab artifact: {path}"

    graph_design, graph_nodes = _load_bundle(path)
    assert graph_design["id"] == expected_id
    assert graph_design["agent_target_id"] == "customer-escalation-triage-target-v1"
    assert graph_design["eval_contract_id"] == "customer-escalation-triage-eval-contract-v1"
    assert len(graph_nodes) >= min_nodes

    node_ids = {node["id"] for node in graph_nodes}
    for node in graph_nodes:
        assert node["purpose"]
        supports_rules = node.get("supports_rules", [])
        assert isinstance(supports_rules, list)
        assert set(supports_rules).issubset(
            {
                "evidence_first_diagnosis",
                "separate_facts_from_hypotheses",
                "identify_recent_changes",
                "assess_customer_impact",
                "recommend_safe_next_actions",
                "draft_customer_safe_update",
            }
        )

    if expected_id.endswith("-v1"):
        assert graph_design.get("source_version") == "v0-baseline"
        assert graph_design.get("fix_plan_id") == "fix-v1-evidence-first-triage"
        assert "separate_facts_hypotheses_unknowns" in node_ids
        assert "collect_trace_evidence" in node_ids


def test_v0_to_v1_graph_diff_has_expected_changes() -> None:
    _, v0_nodes = _load_bundle(TARGET_DIR / "graph-design-v0.yaml")
    _, v1_nodes = _load_bundle(TARGET_DIR / "graph-design.yaml")

    v0_ids = {node["id"] for node in v0_nodes}
    v1_ids = {node["id"] for node in v1_nodes}
    added = v1_ids - v0_ids
    removed = v0_ids - v1_ids

    assert "single_pass_response" in removed
    assert "normalize_evidence" in added
    assert "separate_facts_hypotheses_unknowns" in added
