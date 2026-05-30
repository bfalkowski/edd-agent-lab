"""Reference publish artifacts for Customer Escalation Triage (HLD-005)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from edd_agent_lab.paths import REPO_ROOT

REFERENCE_SCENARIO = "customer_escalation_triage"
FIXTURES_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "reference" / "escalation-publish-artifacts.json"
)


def resolve_platform_examples_dir() -> Path | None:
    configured = os.environ.get("EDD_PLATFORM_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser() / "examples" / REFERENCE_SCENARIO
        if candidate.is_dir():
            return candidate
    sibling = REPO_ROOT.parent / "eval-driven-design-platform" / "examples" / REFERENCE_SCENARIO
    if sibling.is_dir():
        return sibling
    return None


def _load_yaml_mapping(path: Path, key: str) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        msg = f"Expected mapping in {path}"
        raise ValueError(msg)
    block = document.get(key)
    if not isinstance(block, dict):
        msg = f"Expected {key} mapping in {path}"
        raise ValueError(msg)
    return dict(block)


def _load_trace_links(path: Path) -> list[dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        msg = f"Expected mapping in {path}"
        raise ValueError(msg)
    links = document.get("trace_links")
    if not isinstance(links, list):
        msg = f"Expected trace_links list in {path}"
        raise ValueError(msg)
    return [dict(item) for item in links if isinstance(item, dict)]


def load_reference_publish_artifacts() -> dict[str, Any]:
    examples_dir = resolve_platform_examples_dir()
    if examples_dir is not None:
        return {
            "failure_packet": _load_yaml_mapping(
                examples_dir / "failure-packet-v0.yaml",
                "failure_packet",
            ),
            "trace_links_v0": _load_trace_links(examples_dir / "trace-link-v0.yaml"),
            "trace_links_v1": _load_trace_links(examples_dir / "trace-link-v1.yaml"),
            "fix_plan": _load_yaml_mapping(examples_dir / "fix-plan-v1.yaml", "fix_plan"),
            "comparison": _load_yaml_mapping(
                examples_dir / "comparison-v0-v1.yaml",
                "comparison",
            ),
            "gate_result": _load_yaml_mapping(examples_dir / "gate-result-v1.yaml", "gate_result"),
            "agent": _load_yaml_mapping(examples_dir / "agent-target.yaml", "agent"),
            "target": _load_yaml_mapping(examples_dir / "agent-target.yaml", "agent_target"),
            "eval_contract": _load_yaml_mapping(
                examples_dir / "eval-contract.yaml",
                "eval_contract",
            ),
        }

    if not FIXTURES_PATH.is_file():
        msg = f"Reference publish fixtures missing: {FIXTURES_PATH}"
        raise FileNotFoundError(msg)
    loaded = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        msg = f"Expected mapping in {FIXTURES_PATH}"
        raise ValueError(msg)
    return loaded


def enrich_escalation_run_record(
    run_record: dict[str, Any],
    *,
    agent_version: str,
) -> dict[str, Any]:
    """Attach HLD-005 publish artifacts for platform ingest."""
    artifacts = load_reference_publish_artifacts()
    enriched = dict(run_record)

    if agent_version == "v0-baseline":
        enriched["failure_packet"] = dict(artifacts["failure_packet"])
        enriched["trace_links"] = list(artifacts["trace_links_v0"])
        enriched.pop("publish_schema_version", None)
        return enriched

    if agent_version == "v1-evidence-triage-graph":
        enriched["publish_schema_version"] = "2"
        enriched["agent"] = {
            "id": artifacts["agent"]["id"],
            "name": artifacts["agent"]["name"],
        }
        enriched["target"] = {"id": artifacts["target"]["id"]}
        enriched["eval_contract"] = {"id": artifacts["eval_contract"]["id"]}
        enriched["tool_context"] = {
            "tool_mode_summary": "mock_local",
            "production_ready": False,
        }
        enriched["producer"] = {
            "name": "edd-agent-lab",
            "environment": "local_demo",
            "run_mode": "mock_local",
        }
        enriched["agent_version"] = {
            "id": "v1-evidence-triage-graph",
            "version_label": "v1-evidence-triage-graph",
            "agent_id": artifacts["agent"]["id"],
            "target_id": artifacts["target"]["id"],
            "eval_contract_id": artifacts["eval_contract"]["id"],
            "graph_design_id": "customer-escalation-triage-graph-v1",
            "tool_mode_summary": "mock_local",
        }
        enriched["failure_packet"] = None
        enriched["fix_plan"] = dict(artifacts["fix_plan"])
        enriched["comparison"] = dict(artifacts["comparison"])
        enriched["gate_result"] = dict(artifacts["gate_result"])
        enriched["trace_links"] = list(artifacts["trace_links_v1"])
        return enriched

    return enriched
