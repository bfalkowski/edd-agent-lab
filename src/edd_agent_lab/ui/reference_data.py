"""Reference scenario mock data and artifact view helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml

from edd_agent_lab.integrations.reference_publish import resolve_platform_examples_dir
from edd_agent_lab.paths import REPO_ROOT

MOCK_DATA_DIR = REPO_ROOT / "data" / "mock" / "customer_escalation_triage" / "apex_health"
MOCK_FILES = (
    "customer_report",
    "langfuse_trace_summary",
    "eval_results",
    "recent_changes",
    "tool_health",
    "customer_context",
)
TARGET_DIR = REPO_ROOT / "lab-runs" / "customer_escalation_triage" / "target"

SCORE_RULE_MAP: dict[str, list[str]] = {
    "diagnostic_grounding": ["evidence_first_diagnosis", "separate_facts_from_hypotheses"],
    "change_correlation_quality": ["identify_recent_changes"],
    "impact_assessment_quality": ["assess_customer_impact"],
    "action_plan_quality": ["recommend_safe_next_actions"],
    "customer_communication_quality": ["draft_customer_safe_update"],
}

GRAPH_NODE_EXPLANATIONS: dict[str, dict[str, str]] = {
    "collect_evidence": {
        "why": "Gather evidence before diagnosis",
        "rule": "evidence_first_diagnosis",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "normalize_evidence": {
        "why": "Normalize traces, evals, tools, and changes",
        "rule": "evidence_first_diagnosis",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "identify_correlations": {
        "why": "Connect latency, eval drops, and tool timeouts",
        "rule": "identify_recent_changes",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "separate_facts_hypotheses_unknowns": {
        "why": "Prevent unsupported causality claims",
        "rule": "separate_facts_from_hypotheses",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "customer_safe_update_review": {
        "why": "Avoid speculative external updates",
        "rule": "draft_customer_safe_update",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "collect_trace_evidence": {
        "why": "Pull trace summaries before diagnosis",
        "rule": "evidence_first_diagnosis",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "collect_eval_history": {
        "why": "Ground diagnosis in eval score trends",
        "rule": "evidence_first_diagnosis",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "collect_recent_changes": {
        "why": "Correlate recent deployments with symptoms",
        "rule": "identify_recent_changes",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "collect_tool_health": {
        "why": "Include tool timeout evidence",
        "rule": "evidence_first_diagnosis",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "collect_customer_context": {
        "why": "Load customer context from scenario",
        "rule": "evidence_first_diagnosis",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "parse_escalation_report": {
        "why": "Structure the escalation report before evidence collection",
        "rule": "evidence_first_diagnosis",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "assess_customer_impact": {
        "why": "Quantify customer impact before recommending actions",
        "rule": "assess_customer_impact",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "recommend_mitigation_plan": {
        "why": "Recommend safe next actions from evidence",
        "rule": "recommend_safe_next_actions",
        "failure": "fp-v0-unsupported-root-cause",
    },
    "draft_customer_update": {
        "why": "Draft a customer-facing update from structured findings",
        "rule": "draft_customer_safe_update",
        "failure": "fp-v0-unsupported-root-cause",
    },
}


def load_mock_evidence_bundle() -> dict[str, Any]:
    bundle: dict[str, Any] = {}
    for name in MOCK_FILES:
        path = MOCK_DATA_DIR / f"{name}.json"
        bundle[name] = json.loads(path.read_text(encoding="utf-8"))
    return bundle


def resolve_design_artifact_dir() -> Path:
    if TARGET_DIR.is_dir():
        return TARGET_DIR
    examples = resolve_platform_examples_dir()
    if examples is not None:
        return examples
    msg = "Reference design artifacts not found in lab-runs or platform examples"
    raise FileNotFoundError(msg)


def load_graph_design_bundle(
    version: Literal["v0", "v1"],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base = resolve_design_artifact_dir()
    filename = "graph-design-v0.yaml" if version == "v0" else "graph-design.yaml"
    alt = "graph-design-v1.yaml" if version == "v1" else None
    path = base / filename
    if not path.is_file() and alt:
        path = base / alt
    if not path.is_file():
        msg = f"Graph design artifact missing: {path}"
        raise FileNotFoundError(msg)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected mapping in {path}"
        raise ValueError(msg)
    graph_design = payload["graph_design"]
    graph_nodes = payload.get("graph_nodes", [])
    if not isinstance(graph_design, dict) or not isinstance(graph_nodes, list):
        msg = f"Invalid graph design bundle in {path}"
        raise ValueError(msg)
    return dict(graph_design), [dict(node) for node in graph_nodes if isinstance(node, dict)]


def graph_flow_summary(graph_design: dict[str, Any], graph_nodes: list[dict[str, Any]]) -> str:
    flow = graph_design.get("flow_order")
    if isinstance(flow, list) and flow:
        return " → ".join(str(node) for node in flow)
    if graph_nodes:
        return " → ".join(str(node.get("id", "")) for node in graph_nodes)
    return str(graph_design.get("name", graph_design.get("id", "unknown")))


def graph_diff_rows(
    v0_nodes: list[dict[str, Any]],
    v1_nodes: list[dict[str, Any]],
) -> list[dict[str, str]]:
    v0_ids = {str(node.get("id", "")) for node in v0_nodes}
    v1_ids = {str(node.get("id", "")) for node in v1_nodes}
    rows: list[dict[str, str]] = []
    for node_id in sorted(v1_ids - v0_ids):
        meta = GRAPH_NODE_EXPLANATIONS.get(node_id, {})
        rows.append(
            {
                "added_node": node_id,
                "why_it_exists": meta.get("why", "Supports v1 evidence-first triage"),
                "rule_supported": meta.get("rule", ""),
                "failure_addressed": meta.get("failure", "fp-v0-unsupported-root-cause"),
            }
        )
    return rows


def _load_yaml_list(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        return []
    items = document.get(key)
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def load_tool_binding_rows() -> list[dict[str, Any]]:
    examples = resolve_platform_examples_dir()
    if examples is None:
        return []
    rows = _load_yaml_list(examples / "tool-bindings.yaml", "tool_bindings")
    feasibility = {
        str(item.get("requirement_id", "")): item
        for item in load_tool_feasibility_rows()
    }
    enriched: list[dict[str, Any]] = []
    for row in rows:
        requirement_id = str(row.get("requirement_id", ""))
        review = feasibility.get(requirement_id, {})
        production_blocker = review.get("production_ready") is False or str(
            review.get("implementation_status", "")
        ) in {"mock_only", "local_only"}
        enriched.append(
            {
                "graph_node": row.get("graph_node"),
                "requirement": requirement_id,
                "implementation": row.get("active_implementation"),
                "mode": row.get("mode"),
                "production_blocker": "Yes" if production_blocker else "No",
            }
        )
    return enriched


def load_tool_feasibility_rows() -> list[dict[str, Any]]:
    examples = resolve_platform_examples_dir()
    if examples is None:
        return []
    return _load_yaml_list(examples / "tool-feasibility.yaml", "tool_feasibility")


def list_reference_artifact_paths() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    candidates: list[tuple[str, Path]] = [
        ("graph-design-v0", TARGET_DIR / "graph-design-v0.yaml"),
        ("graph-design-v1", TARGET_DIR / "graph-design.yaml"),
    ]
    examples = resolve_platform_examples_dir()
    if examples is not None:
        candidates.extend(
            [
                ("agent-target", examples / "agent-target.yaml"),
                ("behavior-rules", examples / "behavior-rules.yaml"),
                ("eval-contract", examples / "eval-contract.yaml"),
                ("tool-feasibility", examples / "tool-feasibility.yaml"),
                ("tool-bindings", examples / "tool-bindings.yaml"),
                ("failure-packet-v0", examples / "failure-packet-v0.yaml"),
                ("fix-plan-v1", examples / "fix-plan-v1.yaml"),
                ("comparison-v0-v1", examples / "comparison-v0-v1.yaml"),
                ("gate-result-v1", examples / "gate-result-v1.yaml"),
            ]
        )
    for artifact_type, path in candidates:
        rows.append(
            {
                "artifact_type": artifact_type,
                "path": str(path),
                "status": "present" if path.is_file() else "missing",
            }
        )
    return rows


def comparison_metric_rows(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    score_delta = artifacts.get("comparison", {}).get("score_delta") or {}
    rows: list[dict[str, Any]] = []
    for metric_id, delta in score_delta.items():
        if isinstance(delta, dict):
            rows.append(
                {
                    "metric": metric_id.replace("_", " ").title(),
                    "metric_id": metric_id,
                    "v0": delta.get("v0") or delta.get("baseline"),
                    "v1": delta.get("v1") or delta.get("candidate"),
                    "delta": delta.get("delta"),
                    "rules": ", ".join(SCORE_RULE_MAP.get(metric_id, [])),
                }
            )
    return rows


def reference_overall_score(
    artifacts: dict[str, Any],
    version: Literal["v0", "v1"],
) -> float | None:
    rows = comparison_metric_rows(artifacts)
    if not rows:
        return None
    key = "v0" if version == "v0" else "v1"
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return sum(values) / len(values)


def trace_link_rows(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    link_groups = (
        ("trace_links_v0", "v0-baseline"),
        ("trace_links_v1", "v1-evidence-triage-graph"),
    )
    for key, version in link_groups:
        for link in artifacts.get(key) or []:
            if not isinstance(link, dict):
                continue
            rows.append(
                {
                    "version": version,
                    "run_id": str(link.get("platform_run_id") or link.get("id", "")),
                    "provider": str(link.get("provider", "")),
                    "trace_id": str(link.get("external_trace_id", "")),
                    "tool_mode": str(link.get("tool_mode") or link.get("run_mode") or "fixture"),
                    "environment": str(link.get("environment") or "local_demo"),
                    "external_url": str(link.get("external_url") or ""),
                }
            )
    return rows
