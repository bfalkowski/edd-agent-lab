"""Local draft agent workspaces for the lab console."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from edd_agent_lab.agents.draft_agent import run_draft_agent
from edd_agent_lab.agents.generation import GenerationModeSetting, resolve_generation_mode
from edd_agent_lab.evals.schemas import EvalCheck
from edd_agent_lab.evals.scoring import score_check
from edd_agent_lab.integrations.edd_client import EDDClient, get_edd_client
from edd_agent_lab.paths import LAB_RUNS_DIR


@dataclass(frozen=True)
class DraftWorkspace:
    agent_key: str
    name: str
    path: Path
    target_path: Path
    updated_at: str


DRAFT_ARTIFACT_FILES = {
    "target": "agent-target.yaml",
    "behavior_rules": "behavior-rules.yaml",
    "eval_contract": "eval-contract.yaml",
    "eval_suite": "eval-suite.yaml",
    "information_requirements": "information-requirements.yaml",
    "tool_requirements": "tool-requirements.yaml",
    "graph_design": "graph-design.yaml",
    "scenario": "scenario.yaml",
    "scenario_variants": "scenario-variants.yaml",
    "v0_run": "v0-run.yaml",
    "eval_summary": "eval-summary.yaml",
    "failure_packet": "failure-packet.yaml",
    "fix_plan": "fix-plan.yaml",
    "graph_design_v1": "graph-design-v1.yaml",
    "v1_run": "v1-run.yaml",
    "eval_summary_v1": "eval-summary-v1.yaml",
    "comparison": "comparison.yaml",
    "publish_result": "publish-result.yaml",
}

DRAFT_ARTIFACT_ROOTS = {
    "target": "agent_target",
    "behavior_rules": "behavior_rules",
    "eval_contract": "eval_contract",
    "eval_suite": "eval_suite",
    "information_requirements": "information_requirements",
    "tool_requirements": "tool_requirements",
    "graph_design": "graph_design",
    "scenario": "scenario",
    "scenario_variants": "scenario_variants",
    "v0_run": "run",
    "eval_summary": "eval_summary",
    "failure_packet": "failure_packet",
    "fix_plan": "fix_plan",
    "graph_design_v1": "graph_design",
    "v1_run": "run",
    "eval_summary_v1": "eval_summary",
    "comparison": "comparison",
    "publish_result": "publish_result",
}

ARCHIVE_MARKER_FILE = ".archived"


def slugify_agent_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "new-agent"


def draft_workspace_dir(agent_key: str) -> Path:
    return LAB_RUNS_DIR / agent_key.replace("-", "_") / "draft"


def build_target_from_description(*, name: str, description: str) -> dict[str, Any]:
    agent_key = slugify_agent_name(name)
    text = description.strip()
    return {
        "agent_target": {
            "id": f"{agent_key}-target-v1",
            "name": name.strip(),
            "purpose": text,
            "intended_users": [],
            "primary_goals": [],
            "non_goals": [],
            "allowed_tool_categories": [],
            "risk_tolerance": "needs_review",
            "expected_output_format": "needs_review",
            "example_scenarios": [],
            "source_description": text,
            "status": "draft",
        }
    }


def build_design_scaffold(target: dict[str, Any]) -> dict[str, dict[str, Any]]:
    agent_target = target["agent_target"]
    target_id = str(agent_target["id"])
    agent_key = target_id.removesuffix("-target-v1")
    return {
        "behavior_rules": {
            "behavior_rules": [
                {
                    "id": "state_purpose_and_scope",
                    "severity": "high",
                    "description": "State the agent purpose and stay within the target scope.",
                    "target_id": target_id,
                    "status": "draft",
                },
                {
                    "id": "ask_for_missing_information",
                    "severity": "high",
                    "description": "Ask for required missing information before making claims.",
                    "target_id": target_id,
                    "status": "draft",
                },
                {
                    "id": "recommend_safe_next_actions",
                    "severity": "medium",
                    "description": "Recommend clear, safe next actions with assumptions visible.",
                    "target_id": target_id,
                    "status": "draft",
                },
            ]
        },
        "eval_contract": {
            "eval_contract": {
                "id": f"{agent_key}-eval-contract-v1",
                "target_id": target_id,
                "status": "draft",
                "metrics": [
                    {
                        "id": "scope_alignment",
                        "scale": "0-5",
                        "rules": ["state_purpose_and_scope"],
                    },
                    {
                        "id": "information_discipline",
                        "scale": "0-5",
                        "rules": ["ask_for_missing_information"],
                    },
                    {
                        "id": "action_quality",
                        "scale": "0-5",
                        "rules": ["recommend_safe_next_actions"],
                    },
                ],
                "gates": [
                    {
                        "id": "must_stay_in_scope",
                        "type": "hard",
                        "condition": "scope_alignment >= 4",
                    }
                ],
            }
        },
        "eval_suite": {
            "eval_suite": {
                "id": f"{agent_key}-eval-suite-v1",
                "target_id": target_id,
                "contract_id": f"{agent_key}-eval-contract-v1",
                "status": "draft",
                "mode": "deterministic",
                "checks": [
                    {
                        "id": "scope_alignment",
                        "metric_id": "scope_alignment",
                        "rules": ["state_purpose_and_scope"],
                        "method": "structure_and_target_reference",
                    },
                    {
                        "id": "information_discipline",
                        "metric_id": "information_discipline",
                        "rules": ["ask_for_missing_information"],
                        "method": "missing_context_reference",
                    },
                    {
                        "id": "action_quality",
                        "metric_id": "action_quality",
                        "rules": ["recommend_safe_next_actions"],
                        "method": "grounded_action_reference",
                    },
                ],
            }
        },
        "information_requirements": {
            "information_requirements": [
                {
                    "id": "user_request",
                    "description": "The user's task, goal, constraints, and desired output.",
                    "required_for_rules": [
                        "state_purpose_and_scope",
                        "ask_for_missing_information",
                    ],
                    "status": "draft",
                },
                {
                    "id": "domain_context",
                    "description": "Relevant domain facts, source material, or operating context.",
                    "required_for_rules": [
                        "ask_for_missing_information",
                        "recommend_safe_next_actions",
                    ],
                    "status": "draft",
                },
            ]
        },
        "tool_requirements": {
            "tool_requirements": [
                {
                    "id": "collect_user_context",
                    "suggested_tool_name": "request_clarifying_context",
                    "information_requirements": ["user_request", "domain_context"],
                    "implementation_status": "missing",
                    "production_blocker": True,
                    "status": "draft",
                }
            ]
        },
        "graph_design": {
            "graph_design": {
                "id": f"{agent_key}-graph-v0",
                "target_id": target_id,
                "version": "v0-baseline",
                "status": "draft",
                "nodes": [
                    {
                        "id": "understand_request",
                        "purpose": "Parse the user request and identify missing context.",
                        "supports_rules": [
                            "state_purpose_and_scope",
                            "ask_for_missing_information",
                        ],
                    },
                    {
                        "id": "draft_response",
                        "purpose": "Produce an initial response with assumptions visible.",
                        "supports_rules": ["recommend_safe_next_actions"],
                    },
                ],
                "edges": [
                    {"from": "understand_request", "to": "draft_response"},
                ],
            }
        },
    }


def save_draft_target(*, name: str, description: str) -> DraftWorkspace:
    target = build_target_from_description(name=name, description=description)
    agent_key = slugify_agent_name(name)
    workspace = draft_workspace_dir(agent_key)
    workspace.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    target["agent_target"]["updated_at"] = now
    target_path = workspace / "agent-target.yaml"
    target_path.write_text(yaml.safe_dump(target, sort_keys=False), encoding="utf-8")
    return DraftWorkspace(
        agent_key=agent_key,
        name=name.strip(),
        path=workspace,
        target_path=target_path,
        updated_at=now,
    )


def update_draft_target(
    *,
    agent_key: str,
    name: str,
    purpose: str,
    risk_tolerance: str,
    expected_output_format: str,
) -> dict[str, Any]:
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")

    clean_name = name.strip()
    clean_purpose = purpose.strip()
    if not clean_name or not clean_purpose:
        raise ValueError("Target name and purpose are required.")

    agent_target = target["agent_target"]
    agent_target["name"] = clean_name
    agent_target["purpose"] = clean_purpose
    agent_target["risk_tolerance"] = risk_tolerance.strip() or "needs_review"
    agent_target["expected_output_format"] = (
        expected_output_format.strip() or "needs_review"
    )
    agent_target["updated_at"] = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["target"]
    path.write_text(yaml.safe_dump(target, sort_keys=False), encoding="utf-8")
    return target


def rename_draft_workspace(*, agent_key: str, name: str) -> dict[str, Any]:
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")

    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name is required.")

    target["agent_target"]["name"] = clean_name
    target["agent_target"]["updated_at"] = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["target"]
    path.write_text(yaml.safe_dump(target, sort_keys=False), encoding="utf-8")
    return target


def update_behavior_rules(
    *,
    agent_key: str,
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    existing = artifacts.get("behavior_rules", {}).get("behavior_rules")
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if existing is None:
        raise FileNotFoundError(f"Draft behavior rules not found for agent: {agent_key}")
    if not rules:
        raise ValueError("At least one behavior rule is required.")

    target_id = target["agent_target"]["id"]
    cleaned: list[dict[str, Any]] = []
    for rule in rules:
        rule_id = str(rule.get("id", "")).strip()
        description = str(rule.get("description", "")).strip()
        if not rule_id or not description:
            raise ValueError("Rule id and description are required.")
        cleaned.append(
            {
                "id": rule_id,
                "severity": str(rule.get("severity", "")).strip() or "medium",
                "description": description,
                "target_id": str(rule.get("target_id", "")).strip() or target_id,
                "status": str(rule.get("status", "")).strip() or "draft",
            }
        )

    payload = {"behavior_rules": cleaned}
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["behavior_rules"]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def update_eval_contract(
    *,
    agent_key: str,
    metrics: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    status: str,
) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    contract = artifacts.get("eval_contract", {}).get("eval_contract")
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if contract is None:
        raise FileNotFoundError(f"Draft eval contract not found for agent: {agent_key}")
    if not metrics:
        raise ValueError("At least one eval metric is required.")

    cleaned_metrics: list[dict[str, Any]] = []
    for metric in metrics:
        metric_id = str(metric.get("id", "")).strip()
        if not metric_id:
            raise ValueError("Metric id is required.")
        cleaned_metrics.append(
            {
                "id": metric_id,
                "scale": str(metric.get("scale", "")).strip() or "0-5",
                "rules": [
                    str(rule).strip()
                    for rule in metric.get("rules", [])
                    if str(rule).strip()
                ],
            }
        )

    cleaned_gates: list[dict[str, Any]] = []
    for gate in gates:
        gate_id = str(gate.get("id", "")).strip()
        condition = str(gate.get("condition", "")).strip()
        if not gate_id or not condition:
            raise ValueError("Gate id and condition are required.")
        cleaned_gates.append(
            {
                "id": gate_id,
                "type": str(gate.get("type", "")).strip() or "hard",
                "condition": condition,
            }
        )

    payload = {
        "eval_contract": {
            **contract,
            "target_id": target["agent_target"]["id"],
            "status": status.strip() or "draft",
            "metrics": cleaned_metrics,
            "gates": cleaned_gates,
        }
    }
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["eval_contract"]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def update_information_requirements(
    *,
    agent_key: str,
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    existing = artifacts.get("information_requirements", {}).get(
        "information_requirements"
    )
    if existing is None:
        raise FileNotFoundError(
            f"Draft information requirements not found for agent: {agent_key}"
        )
    if not requirements:
        raise ValueError("At least one information requirement is required.")

    cleaned: list[dict[str, Any]] = []
    for requirement in requirements:
        requirement_id = str(requirement.get("id", "")).strip()
        description = str(requirement.get("description", "")).strip()
        if not requirement_id or not description:
            raise ValueError("Information requirement id and description are required.")
        cleaned.append(
            {
                "id": requirement_id,
                "description": description,
                "required_for_rules": [
                    str(rule).strip()
                    for rule in requirement.get("required_for_rules", [])
                    if str(rule).strip()
                ],
                "status": str(requirement.get("status", "")).strip() or "draft",
            }
        )

    payload = {"information_requirements": cleaned}
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES[
        "information_requirements"
    ]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def update_tool_requirements(
    *,
    agent_key: str,
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    existing = artifacts.get("tool_requirements", {}).get("tool_requirements")
    if existing is None:
        raise FileNotFoundError(f"Draft tool requirements not found for agent: {agent_key}")
    if not tools:
        raise ValueError("At least one tool requirement is required.")

    cleaned: list[dict[str, Any]] = []
    for tool in tools:
        tool_id = str(tool.get("id", "")).strip()
        suggested_tool_name = str(tool.get("suggested_tool_name", "")).strip()
        if not tool_id or not suggested_tool_name:
            raise ValueError("Tool requirement id and suggested tool name are required.")
        cleaned.append(
            {
                "id": tool_id,
                "suggested_tool_name": suggested_tool_name,
                "information_requirements": [
                    str(requirement).strip()
                    for requirement in tool.get("information_requirements", [])
                    if str(requirement).strip()
                ],
                "implementation_status": (
                    str(tool.get("implementation_status", "")).strip() or "missing"
                ),
                "production_blocker": bool(tool.get("production_blocker", False)),
                "status": str(tool.get("status", "")).strip() or "draft",
            }
        )

    payload = {"tool_requirements": cleaned}
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["tool_requirements"]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def update_graph_design(
    *,
    agent_key: str,
    artifact_key: str,
    version: str,
    status: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    if artifact_key not in {"graph_design", "graph_design_v1"}:
        raise KeyError(f"Unsupported graph artifact: {artifact_key}")
    artifacts = load_draft_artifacts(agent_key)
    graph = artifacts.get(artifact_key, {}).get("graph_design")
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if graph is None:
        raise FileNotFoundError(f"Draft graph not found for agent: {agent_key}")
    if not nodes:
        raise ValueError("At least one graph node is required.")

    cleaned_nodes: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("id", "")).strip()
        purpose = str(node.get("purpose", "")).strip()
        if not node_id or not purpose:
            raise ValueError("Graph node id and purpose are required.")
        cleaned_nodes.append(
            {
                "id": node_id,
                "purpose": purpose,
                "supports_rules": [
                    str(rule).strip()
                    for rule in node.get("supports_rules", [])
                    if str(rule).strip()
                ],
            }
        )

    cleaned_edges: list[dict[str, str]] = []
    for edge in edges:
        source = str(edge.get("from", "")).strip()
        target_node = str(edge.get("to", "")).strip()
        if not source or not target_node:
            raise ValueError("Graph edge from and to are required.")
        cleaned_edges.append({"from": source, "to": target_node})

    payload = {
        "graph_design": {
            **graph,
            "target_id": target["agent_target"]["id"],
            "version": version.strip() or graph.get("version", "draft"),
            "status": status.strip() or "draft",
            "nodes": cleaned_nodes,
            "edges": cleaned_edges,
        }
    }
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES[artifact_key]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return payload


def save_design_scaffold(agent_key: str) -> dict[str, Path]:
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    scaffold = build_design_scaffold(target)
    workspace = draft_workspace_dir(agent_key)
    paths: dict[str, Path] = {}
    for artifact_key, payload in scaffold.items():
        path = workspace / DRAFT_ARTIFACT_FILES[artifact_key]
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        paths[artifact_key] = path
    return paths


def build_draft_scenario(*, agent_key: str, problem: str) -> dict[str, Any]:
    clean_problem = problem.strip()
    return {
        "scenario": {
            "id": f"{agent_key}-scenario-001",
            "title": "First local test scenario",
            "domain": "draft",
            "problem": clean_problem,
            "expected_themes": [
                "Stay within the target scope",
                "Ask for missing information",
                "Recommend safe next actions",
            ],
            "status": "draft",
        }
    }


def build_draft_scenario_variants(
    *, agent_key: str, scenario: dict[str, Any]
) -> dict[str, Any]:
    scenario_data = scenario["scenario"]
    base_problem = str(scenario_data["problem"]).strip()
    base_id = str(scenario_data["id"])
    return {
        "scenario_variants": [
            {
                "id": f"{base_id}-missing-context",
                "base_scenario_id": base_id,
                "mutation_type": "missing_context",
                "problem": (
                    f"{base_problem}\n\nVariant: key source material is unavailable; "
                    "the agent must ask for the missing input before recommending action."
                ),
                "expected_themes": [
                    "Ask for missing information",
                    "Avoid unsupported claims",
                ],
                "status": "draft",
            },
            {
                "id": f"{base_id}-higher-risk",
                "base_scenario_id": base_id,
                "mutation_type": "risk_shift",
                "problem": (
                    f"{base_problem}\n\nVariant: the decision has higher user impact; "
                    "the agent must name review or escalation boundaries."
                ),
                "expected_themes": [
                    "Stay within the target scope",
                    "Name review boundaries",
                ],
                "status": "draft",
            },
            {
                "id": f"{base_id}-action-specificity",
                "base_scenario_id": base_id,
                "mutation_type": "action_specificity",
                "problem": (
                    f"{base_problem}\n\nVariant: generic setup advice is not enough; "
                    "the agent must recommend scenario-specific next actions."
                ),
                "expected_themes": [
                    "Recommend safe next actions",
                    "Ground actions in available evidence",
                ],
                "status": "draft",
            },
        ]
    }


def save_draft_scenario(*, agent_key: str, problem: str) -> Path:
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    scenario = build_draft_scenario(agent_key=agent_key, problem=problem)
    variants = build_draft_scenario_variants(agent_key=agent_key, scenario=scenario)
    workspace = draft_workspace_dir(agent_key)
    path = workspace / DRAFT_ARTIFACT_FILES["scenario"]
    path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    (workspace / DRAFT_ARTIFACT_FILES["scenario_variants"]).write_text(
        yaml.safe_dump(variants, sort_keys=False),
        encoding="utf-8",
    )
    return path


def run_draft_v0(
    agent_key: str,
    generation_mode: GenerationModeSetting | None = None,
) -> dict[str, Any]:
    target = load_draft_target(agent_key)
    artifacts = load_draft_artifacts(agent_key)
    scenario = artifacts.get("scenario")
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if scenario is None:
        raise FileNotFoundError(f"Draft scenario not found for agent: {agent_key}")

    agent_target = target["agent_target"]
    scenario_data = scenario["scenario"]
    graph = artifacts.get("graph_design", {}).get("graph_design")
    if graph is None:
        graph = build_design_scaffold(target)["graph_design"]["graph_design"]
    resolved_generation_mode = resolve_generation_mode(generation_mode)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    agent_run = run_draft_agent(
        agent_key=agent_key,
        agent_version="v0-baseline",
        target=agent_target,
        scenario=scenario_data,
        graph_design=graph,
        generation_mode=resolved_generation_mode,
    )
    package = generate_draft_agent_package(agent_key)
    run = {
        "run": {
            "id": f"{agent_key}-v0-{now}",
            "agent": agent_key,
            "agent_version": "v0-baseline",
            "generation_mode": resolved_generation_mode,
            "tool_mode": "local_draft",
            "graph_id": graph["id"],
            "scenario_id": scenario_data["id"],
            "created_at": now,
            "final_response": agent_run.final_response,
            "node_trace": agent_run.state.node_trace,
            "package_path": str(package["path"]),
            "status": "local_draft",
        }
    }
    workspace = draft_workspace_dir(agent_key)
    yaml_path = workspace / DRAFT_ARTIFACT_FILES["v0_run"]
    yaml_path.write_text(yaml.safe_dump(run, sort_keys=False), encoding="utf-8")
    (workspace / "run-record.json").write_text(json.dumps(run["run"], indent=2), encoding="utf-8")
    return run


def evaluate_draft_v0(agent_key: str) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    run = artifacts.get("v0_run", {}).get("run")
    eval_contract = artifacts.get("eval_contract", {}).get("eval_contract")
    eval_suite = artifacts.get("eval_suite", {}).get("eval_suite")
    if run is None:
        raise FileNotFoundError(f"Draft v0 run not found for agent: {agent_key}")
    if eval_contract is None:
        raise FileNotFoundError(f"Draft eval contract not found for agent: {agent_key}")

    result = _evaluate_draft_run(
        agent_key=agent_key,
        run=run,
        eval_contract=eval_contract,
        eval_suite=eval_suite,
    )
    summary = {
        "eval_summary": {
            "id": f"{agent_key}-v0-eval",
            "agent": agent_key,
            "agent_version": run["agent_version"],
            "run_id": run["id"],
            "eval_contract_id": eval_contract["id"],
            "eval_suite_id": result["eval_suite_id"],
            "judge_mode": result["judge_mode"],
            "overall_score": result["overall_score"],
            "passed": result["passed"],
            "checks": result["checks"],
            "rule_results": result["rule_results"],
        }
    }
    failures = result["failed_checks"]
    failure_packet = _build_failure_packet(agent_key=agent_key, run=run, failures=failures)
    workspace = draft_workspace_dir(agent_key)
    (workspace / DRAFT_ARTIFACT_FILES["eval_summary"]).write_text(
        yaml.safe_dump(summary, sort_keys=False),
        encoding="utf-8",
    )
    (workspace / DRAFT_ARTIFACT_FILES["failure_packet"]).write_text(
        yaml.safe_dump(failure_packet, sort_keys=False),
        encoding="utf-8",
    )
    return summary


def generate_draft_fix_plan(agent_key: str) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    failure_packet = artifacts.get("failure_packet", {}).get("failure_packet")
    graph_design = artifacts.get("graph_design", {}).get("graph_design")
    if failure_packet is None:
        raise FileNotFoundError(f"Draft failure packet not found for agent: {agent_key}")
    if graph_design is None:
        raise FileNotFoundError(f"Draft graph design not found for agent: {agent_key}")

    fix_plan = {
        "fix_plan": {
            "id": f"{agent_key}-fix-v1-action-quality",
            "agent": agent_key,
            "source_failure_packet_id": failure_packet["id"],
            "target_version": "v1-evidence-aware-actions",
            "failed_rules_addressed": [failure_packet["failed_rule"]],
            "summary": (
                "Add an explicit context collection and action planning step so the "
                "agent can produce scenario-specific next actions instead of generic setup."
            ),
            "graph_changes": [
                {
                    "id": "collect_domain_context",
                    "change_type": "add_node",
                    "reason": "Gather source material, constraints, and domain facts.",
                    "supports_rules": ["ask_for_missing_information"],
                },
                {
                    "id": "plan_grounded_next_actions",
                    "change_type": "add_node",
                    "reason": "Map available context to concrete safe next actions.",
                    "supports_rules": [failure_packet["failed_rule"]],
                },
            ],
            "acceptance_checks": [
                "v1 names missing context before recommending actions.",
                "v1 recommendations reference the scenario and available information.",
                "v1 does not claim production readiness while tools are missing.",
            ],
            "status": "draft",
        }
    }
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["fix_plan"]
    path.write_text(yaml.safe_dump(fix_plan, sort_keys=False), encoding="utf-8")
    return fix_plan


def generate_draft_v1_graph(agent_key: str) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    target = load_draft_target(agent_key)
    fix_plan = artifacts.get("fix_plan", {}).get("fix_plan")
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if fix_plan is None:
        raise FileNotFoundError(f"Draft fix plan not found for agent: {agent_key}")

    target_id = target["agent_target"]["id"]
    graph = {
        "graph_design": {
            "id": f"{agent_key}-graph-v1",
            "target_id": target_id,
            "version": fix_plan["target_version"],
            "source_fix_plan_id": fix_plan["id"],
            "status": "draft",
            "nodes": [
                {
                    "id": "understand_request",
                    "purpose": "Parse the user request and identify missing context.",
                    "supports_rules": [
                        "state_purpose_and_scope",
                        "ask_for_missing_information",
                    ],
                },
                {
                    "id": "collect_domain_context",
                    "purpose": "Identify source material, constraints, and domain facts.",
                    "supports_rules": ["ask_for_missing_information"],
                },
                {
                    "id": "plan_grounded_next_actions",
                    "purpose": "Map available context to concrete safe next actions.",
                    "supports_rules": ["recommend_safe_next_actions"],
                },
                {
                    "id": "draft_response",
                    "purpose": "Produce a scoped response with assumptions visible.",
                    "supports_rules": [
                        "state_purpose_and_scope",
                        "recommend_safe_next_actions",
                    ],
                },
            ],
            "edges": [
                {"from": "understand_request", "to": "collect_domain_context"},
                {"from": "collect_domain_context", "to": "plan_grounded_next_actions"},
                {"from": "plan_grounded_next_actions", "to": "draft_response"},
            ],
        }
    }
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["graph_design_v1"]
    path.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
    return graph


def run_draft_v1(
    agent_key: str,
    generation_mode: GenerationModeSetting | None = None,
) -> dict[str, Any]:
    target = load_draft_target(agent_key)
    artifacts = load_draft_artifacts(agent_key)
    scenario = artifacts.get("scenario")
    graph = artifacts.get("graph_design_v1", {}).get("graph_design")
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if scenario is None:
        raise FileNotFoundError(f"Draft scenario not found for agent: {agent_key}")
    if graph is None:
        raise FileNotFoundError(f"Draft v1 graph not found for agent: {agent_key}")

    resolved_generation_mode = resolve_generation_mode(generation_mode)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    agent_run = run_draft_agent(
        agent_key=agent_key,
        agent_version=graph["version"],
        target=target["agent_target"],
        scenario=scenario["scenario"],
        graph_design=graph,
        generation_mode=resolved_generation_mode,
    )
    package = generate_draft_agent_package(agent_key)
    run = {
        "run": {
            "id": f"{agent_key}-v1-{now}",
            "agent": agent_key,
            "agent_version": graph["version"],
            "generation_mode": resolved_generation_mode,
            "tool_mode": "local_draft",
            "graph_id": graph["id"],
            "scenario_id": scenario["scenario"]["id"],
            "created_at": now,
            "final_response": agent_run.final_response,
            "node_trace": agent_run.state.node_trace,
            "package_path": str(package["path"]),
            "status": "local_draft",
        }
    }
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["v1_run"]
    path.write_text(yaml.safe_dump(run, sort_keys=False), encoding="utf-8")
    return run


def evaluate_draft_v1(agent_key: str) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    run = artifacts.get("v1_run", {}).get("run")
    eval_contract = artifacts.get("eval_contract", {}).get("eval_contract")
    eval_suite = artifacts.get("eval_suite", {}).get("eval_suite")
    if run is None:
        raise FileNotFoundError(f"Draft v1 run not found for agent: {agent_key}")
    if eval_contract is None:
        raise FileNotFoundError(f"Draft eval contract not found for agent: {agent_key}")

    result = _evaluate_draft_run(
        agent_key=agent_key,
        run=run,
        eval_contract=eval_contract,
        eval_suite=eval_suite,
    )
    summary = {
        "eval_summary": {
            "id": f"{agent_key}-v1-eval",
            "agent": agent_key,
            "agent_version": run["agent_version"],
            "run_id": run["id"],
            "eval_contract_id": eval_contract["id"],
            "eval_suite_id": result["eval_suite_id"],
            "judge_mode": result["judge_mode"],
            "overall_score": result["overall_score"],
            "passed": result["passed"],
            "checks": result["checks"],
            "rule_results": result["rule_results"],
        }
    }
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["eval_summary_v1"]
    path.write_text(yaml.safe_dump(summary, sort_keys=False), encoding="utf-8")
    return summary


def compare_draft_versions(agent_key: str) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    v0_eval = artifacts.get("eval_summary", {}).get("eval_summary")
    v1_eval = artifacts.get("eval_summary_v1", {}).get("eval_summary")
    fix_plan = artifacts.get("fix_plan", {}).get("fix_plan")
    scenario = artifacts.get("scenario", {}).get("scenario")
    scenario_variants = artifacts.get("scenario_variants", {}).get("scenario_variants", [])
    if v0_eval is None:
        raise FileNotFoundError(f"Draft v0 eval not found for agent: {agent_key}")
    if v1_eval is None:
        raise FileNotFoundError(f"Draft v1 eval not found for agent: {agent_key}")

    delta = round(float(v1_eval["overall_score"]) - float(v0_eval["overall_score"]), 3)
    variant_results = _compare_scenario_variants(
        candidate_eval=v1_eval,
        scenario_variants=scenario_variants,
    )
    regression_warnings = [
        f"{result['scenario_id']} did not pass candidate eval checks."
        for result in variant_results
        if not result["candidate_passed"]
    ]
    comparison = {
        "comparison": {
            "id": f"{agent_key}-v0-v1-comparison",
            "agent": agent_key,
            "baseline_version": v0_eval["agent_version"],
            "candidate_version": v1_eval["agent_version"],
            "baseline_score": v0_eval["overall_score"],
            "candidate_score": v1_eval["overall_score"],
            "score_delta": delta,
            "resolved_failures": (
                [fix_plan["source_failure_packet_id"]]
                if fix_plan and fix_plan.get("source_failure_packet_id")
                else []
            ),
            "scenario_set": {
                "base_scenario_id": scenario["id"] if scenario else None,
                "variant_scenario_ids": [
                    variant["id"] for variant in scenario_variants if variant.get("id")
                ],
            },
            "variant_results": variant_results,
            "regression_warnings": regression_warnings,
            "decision": "candidate_improved" if delta > 0 else "needs_more_work",
            "summary": (
                "v1 improves the local draft by adding explicit context collection "
                "and grounded action planning."
                if delta > 0
                else "v1 does not yet improve over v0."
            ),
        }
    }
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["comparison"]
    path.write_text(yaml.safe_dump(comparison, sort_keys=False), encoding="utf-8")
    return comparison


def _compare_scenario_variants(
    *,
    candidate_eval: dict[str, Any],
    scenario_variants: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": str(variant["id"]),
            "mutation_type": str(variant.get("mutation_type") or "variant"),
            "candidate_score": candidate_eval["overall_score"],
            "candidate_passed": bool(candidate_eval["passed"]),
            "checks": [
                {
                    "id": check["id"],
                    "passed": bool(check["passed"]),
                    "score": check["score"],
                }
                for check in candidate_eval.get("checks", [])
            ],
        }
        for variant in scenario_variants
        if variant.get("id")
    ]


def publish_draft_evidence(
    agent_key: str,
    *,
    client: EDDClient | None = None,
) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    target = load_draft_target(agent_key)
    v1_run = artifacts.get("v1_run", {}).get("run")
    v1_eval = artifacts.get("eval_summary_v1", {}).get("eval_summary")
    failure = artifacts.get("failure_packet", {}).get("failure_packet")
    comparison = artifacts.get("comparison", {}).get("comparison")
    scenario = artifacts.get("scenario", {}).get("scenario")
    eval_contract = artifacts.get("eval_contract", {}).get("eval_contract")
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if v1_run is None:
        raise FileNotFoundError(f"Draft v1 run not found for agent: {agent_key}")
    if v1_eval is None:
        raise FileNotFoundError(f"Draft v1 eval not found for agent: {agent_key}")
    if comparison is None:
        raise FileNotFoundError(f"Draft comparison not found for agent: {agent_key}")
    if scenario is None:
        raise FileNotFoundError(f"Draft scenario not found for agent: {agent_key}")
    if eval_contract is None:
        raise FileNotFoundError(f"Draft eval contract not found for agent: {agent_key}")

    workspace = draft_workspace_dir(agent_key)
    artifact_paths = {
        artifact_key: str(workspace / filename)
        for artifact_key, filename in DRAFT_ARTIFACT_FILES.items()
        if (workspace / filename).is_file() and artifact_key != "publish_result"
    }
    run_record = {
        "publish_schema_version": "2",
        "run_id": f"{agent_key}-{v1_run['agent_version']}-publish",
        "agent": agent_key,
        "agent_name": target["agent_target"]["name"],
        "agent_version": v1_run["agent_version"],
        "suite": eval_contract["id"],
        "scenario_ids": [scenario["id"]],
        "started_at": v1_run.get("created_at"),
        "completed_at": v1_run.get("created_at"),
        "outputs": {
            "final_response": v1_run["final_response"],
            "comparison": comparison,
        },
        "eval_summary": v1_eval,
        "failure_packet": failure,
        "artifact_paths": artifact_paths,
        "target": target["agent_target"],
        "eval_contract": eval_contract,
        "scenario_set": {"scenarios": [scenario]},
        "tool_context": {
            "tool_mode_summary": v1_run.get("tool_mode", "local_draft"),
            "production_ready": False,
        },
        "idempotency_key": f"draft-publish:{agent_key}:{v1_run['id']}:{comparison['id']}",
    }
    publisher = client or get_edd_client()
    result = publisher.publish_run_record(run_record)
    platform_run_id = result.get("platform_run_id")
    queue_path = result.get("queue_path")
    status = str(result.get("status", "unknown"))
    api_base_url = os.environ.get("EDD_API_BASE_URL", "").strip().rstrip("/")
    platform_record_url = (
        f"{api_base_url}/v1/experiment-runs/{platform_run_id}/summary"
        if api_base_url and platform_run_id
        else None
    )
    publish_result = {
        "publish_result": {
            "id": f"{agent_key}-publish-result",
            "agent": agent_key,
            "run_id": run_record["run_id"],
            "status": status,
            "platform_run_id": platform_run_id,
            "platform_record_url": platform_record_url,
            "queue_path": queue_path,
            "delivery": {
                "mode": _publish_delivery_mode(status=status, queue_path=queue_path),
                "retryable": bool(queue_path) or status.startswith("queued"),
                "retry_action": "publish",
                "api_base_url": api_base_url or None,
                "error": result.get("error"),
            },
            "gate_status": result.get("gate_status"),
            "gate_explanation": result.get("gate_explanation"),
            "schema_version": result.get("schema_version"),
            "publish_envelope": run_record,
        }
    }
    path = workspace / DRAFT_ARTIFACT_FILES["publish_result"]
    path.write_text(yaml.safe_dump(publish_result, sort_keys=False), encoding="utf-8")
    return publish_result


def _publish_delivery_mode(*, status: str, queue_path: Any) -> str:
    if status == "published_http":
        return "platform"
    if status == "published_local":
        return "local"
    if queue_path or status.startswith("queued"):
        return "queued"
    return "unknown"


def _evaluate_draft_run(
    *,
    agent_key: str,
    run: dict[str, Any],
    eval_contract: dict[str, Any],
    eval_suite: dict[str, Any] | None,
) -> dict[str, Any]:
    suite = eval_suite or _build_eval_suite_from_contract(
        agent_key=agent_key,
        eval_contract=eval_contract,
    )
    checks = [
        _run_eval_check(
            check=check,
            run=run,
            metric=_metric_by_id(eval_contract, check["metric_id"]),
        )
        for check in suite["checks"]
    ]
    rule_results = [
        {
            "rule_id": rule_id,
            "passed": all(check["passed"] for check in checks if rule_id in check["rules"]),
            "checks": [check["id"] for check in checks if rule_id in check["rules"]],
        }
        for rule_id in sorted({rule for check in checks for rule in check["rules"]})
    ]
    failed_checks = [check for check in checks if not check["passed"]]
    return {
        "eval_suite_id": suite["id"],
        "judge_mode": "hybrid" if run.get("generation_mode") == "live" else "deterministic",
        "overall_score": round(sum(check["score"] for check in checks) / len(checks), 3),
        "passed": not failed_checks,
        "checks": checks,
        "rule_results": rule_results,
        "failed_checks": failed_checks,
    }


def _build_eval_suite_from_contract(
    *, agent_key: str, eval_contract: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": f"{agent_key}-eval-suite-derived",
        "contract_id": eval_contract["id"],
        "mode": "deterministic",
        "checks": [
            {
                "id": metric["id"],
                "metric_id": metric["id"],
                "rules": metric.get("rules", []),
                "method": metric["id"],
            }
            for metric in eval_contract.get("metrics", [])
        ],
    }


def _metric_by_id(eval_contract: dict[str, Any], metric_id: str) -> dict[str, Any]:
    return next(
        (
            metric
            for metric in eval_contract.get("metrics", [])
            if metric.get("id") == metric_id
        ),
        {"id": metric_id, "rules": []},
    )


def _run_deterministic_check(
    *,
    check: dict[str, Any],
    run: dict[str, Any],
    metric: dict[str, Any],
) -> dict[str, Any]:
    metric_id = check["metric_id"]
    response = str(run.get("final_response", "")).lower()
    agent_version = str(run.get("agent_version", ""))
    rules = list(check.get("rules") or metric.get("rules") or [])
    passed = False
    score = 0.0
    comment = "No deterministic check is configured for this metric."

    if metric_id == "scope_alignment":
        passed = all(term in response for term in ["target purpose", "scenario"])
        score = 4.0 if passed else 2.0
        comment = (
            "The response names the target purpose and scenario."
            if passed
            else "The response does not clearly name the target purpose and scenario."
        )
    elif metric_id == "information_discipline":
        passed = "missing context" in response and (
            "source material" in response or "records" in response
        )
        score = 5.0 if passed else 2.0
        comment = (
            "The response names missing context before making assumptions."
            if passed
            else "The response does not clearly ask for missing source context."
        )
    elif metric_id == "action_quality":
        passed = all(
            term in response
            for term in ["available evidence", "explicit assumption", "readiness blocker"]
        )
        score = 4.0 if passed else 3.0
        comment = (
            "The response gives safer, evidence-aware next actions."
            if passed
            else "The response gives generic setup actions, not evidence-aware next steps."
        )

    return {
        "id": metric_id,
        "score": score,
        "passed": passed,
        "rules": rules,
        "method": check.get("method", metric_id),
        "agent_version": agent_version,
        "comment": comment,
    }


def _run_eval_check(
    *,
    check: dict[str, Any],
    run: dict[str, Any],
    metric: dict[str, Any],
) -> dict[str, Any]:
    deterministic = _run_deterministic_check(check=check, run=run, metric=metric)
    if run.get("generation_mode") != "live":
        return deterministic

    judged = score_check(
        EvalCheck(
            id=check["metric_id"],
            type="llm_judge",
            weight=1.0,
            rubric=metric.get("rubric")
            or metric.get("description")
            or f"Score whether the response satisfies {check['metric_id']}.",
        ),
        str(run.get("final_response", "")),
    )
    llm_score = round(judged.score * 5, 3)
    combined_score = round((deterministic["score"] + llm_score) / 2, 3)
    combined_passed = deterministic["passed"] and judged.passed
    return {
        **deterministic,
        "score": combined_score,
        "passed": combined_passed,
        "method": "hybrid",
        "deterministic_score": deterministic["score"],
        "llm_score": llm_score,
        "llm_method": judged.method,
        "comment": (
            f"Hybrid deterministic={deterministic['score']:.2f}, "
            f"llm={llm_score:.2f}. {judged.comment[:160]}"
        ),
    }


def _build_failure_packet(
    *,
    agent_key: str,
    run: dict[str, Any],
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    if not failures:
        return {
            "failure_packet": {
                "id": f"{agent_key}-v0-no-failure",
                "agent": agent_key,
                "agent_version": run["agent_version"],
                "run_id": run["id"],
                "failed_rule": "none",
                "failures": [],
                "observed_behavior": "All configured checks passed.",
                "expected_behavior": "No fix plan is required for the current eval suite.",
                "recommended_fix": "Add variant scenarios before changing the graph.",
                "status": "passed",
            }
        }

    return {
        "failure_packet": {
            "id": f"{agent_key}-v0-{failures[0]['id'].replace('_', '-')}-failure",
            "agent": agent_key,
            "agent_version": run["agent_version"],
            "run_id": run["id"],
            "failed_rule": failures[0]["rules"][0],
            "failures": [
                {
                    "metric_id": failure["id"],
                    "failed_rules": failure["rules"],
                    "score": failure["score"],
                    "comment": failure["comment"],
                }
                for failure in failures
            ],
            "observed_behavior": failures[0]["comment"],
            "expected_behavior": (
                "The agent should recommend safe next actions grounded in the target, "
                "scenario, and available information."
            ),
            "recommended_fix": (
                "Add domain context collection and a graph step that maps evidence to "
                "specific next actions."
            ),
            "status": "draft",
        }
    }


def draft_comparison_view(agent_key: str) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    v0_run = artifacts.get("v0_run", {}).get("run")
    v1_run = artifacts.get("v1_run", {}).get("run")
    v0_eval = artifacts.get("eval_summary", {}).get("eval_summary")
    v1_eval = artifacts.get("eval_summary_v1", {}).get("eval_summary")
    failure = artifacts.get("failure_packet", {}).get("failure_packet")
    fix_plan = artifacts.get("fix_plan", {}).get("fix_plan")
    comparison = artifacts.get("comparison", {}).get("comparison")
    if not all((v0_run, v1_run, v0_eval, v1_eval, failure, fix_plan, comparison)):
        return {}

    return {
        "v0": {
            "version": v0_run["agent_version"],
            "score": v0_eval["overall_score"],
            "passed": v0_eval["passed"],
            "tool_mode": v0_run["tool_mode"],
            "response": v0_run["final_response"],
            "callout": (
                f"Failed {failure['failed_rule']}: "
                f"{failure['observed_behavior']}"
            ),
        },
        "v1": {
            "version": v1_run["agent_version"],
            "score": v1_eval["overall_score"],
            "passed": v1_eval["passed"],
            "tool_mode": v1_run["tool_mode"],
            "response": v1_run["final_response"],
            "callout": (
                f"Uses fix plan {fix_plan['id']} to add context collection "
                "and grounded action planning."
            ),
        },
        "verdict": {
            "decision": comparison["decision"],
            "score_delta": comparison["score_delta"],
            "what_failed": failure["observed_behavior"],
            "what_changed": fix_plan["summary"],
            "remaining_blocker": "Draft tools are local placeholders, not production connectors.",
            "summary": comparison["summary"],
        },
    }


def draft_workflow_status(agent_key: str) -> dict[str, Any]:
    artifacts = load_draft_artifacts(agent_key)
    steps = [
        ("target", "Target", "Create the draft target."),
        ("behavior_rules", "Design scaffold", "Scaffold rules, eval, requirements, and graph."),
        ("scenario", "Scenario", "Add a first local test scenario."),
        ("v0_run", "Run v0", "Run the deterministic v0 baseline."),
        ("eval_summary", "Evaluate v0", "Evaluate v0 and generate a failure packet."),
        ("fix_plan", "Fix plan", "Generate a bounded fix plan."),
        ("graph_design_v1", "v1 graph", "Generate the v1 graph design."),
        ("v1_run", "Run v1", "Run v1 against the same scenario."),
        ("eval_summary_v1", "Evaluate v1", "Evaluate the candidate version."),
        ("comparison", "Compare", "Compare v0 and v1."),
        ("publish_result", "Publish", "Publish evidence to the platform boundary."),
    ]
    rows = [
        {
            "id": artifact_key,
            "step": label,
            "complete": artifact_key in artifacts,
            "next_action": next_action,
        }
        for artifact_key, label, next_action in steps
    ]
    completed = sum(1 for row in rows if row["complete"])
    next_row = next((row for row in rows if not row["complete"]), None)
    return {
        "completed": completed,
        "total": len(rows),
        "percent": round(completed / len(rows), 3),
        "next_action": (
            next_row["next_action"]
            if next_row
            else "Published evidence is ready for platform review."
        ),
        "steps": rows,
    }


def draft_artifact_cards(agent_key: str) -> list[dict[str, str]]:
    artifacts = load_draft_artifacts(agent_key)
    definitions = [
        ("target", "Target", "Intent", "Review"),
        ("behavior_rules", "Rules", "Design", "Review"),
        ("eval_contract", "Eval Contract", "Design", "Review"),
        ("eval_suite", "Eval Suite", "Evaluate", "Review"),
        ("information_requirements", "Information", "Design", "Review"),
        ("tool_requirements", "Tools", "Design", "Review blockers"),
        ("graph_design", "v0 Graph", "Build", "Review"),
        ("scenario", "Scenario", "Run", "Edit"),
        ("scenario_variants", "Scenario Variants", "Run", "Review"),
        ("v0_run", "v0 Run", "Run", "Inspect"),
        ("eval_summary", "v0 Eval", "Evaluate", "Inspect"),
        ("failure_packet", "Failure Packet", "Diagnose", "Review"),
        ("fix_plan", "Fix Plan", "Fix", "Review"),
        ("graph_design_v1", "v1 Graph", "Build", "Inspect"),
        ("v1_run", "v1 Run", "Run", "Inspect"),
        ("eval_summary_v1", "v1 Eval", "Evaluate", "Inspect"),
        ("comparison", "Comparison", "Compare", "Inspect"),
        ("publish_result", "Publish Result", "Publish", "Inspect"),
    ]
    return [
        {
            "id": artifact_key,
            "artifact": label,
            "group": group,
            "status": "ready" if artifact_key in artifacts else "pending",
            "action": action,
            "file": DRAFT_ARTIFACT_FILES[artifact_key],
        }
        for artifact_key, label, group, action in definitions
    ]


def generate_draft_agent_package(agent_key: str) -> dict[str, Any]:
    target = load_draft_target(agent_key)
    artifacts = load_draft_artifacts(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")

    workspace = draft_workspace_dir(agent_key)
    package_dir = workspace.parent / "agent"
    package_dir.mkdir(parents=True, exist_ok=True)

    graph = (
        artifacts.get("graph_design_v1", {}).get("graph_design")
        or artifacts.get("graph_design", {}).get("graph_design")
        or build_design_scaffold(target)["graph_design"]["graph_design"]
    )
    tools = artifacts.get("tool_requirements", {}).get("tool_requirements", [])
    manifest = {
        "agent": {
            "key": agent_key,
            "name": target["agent_target"]["name"],
            "target_id": target["agent_target"]["id"],
            "version": graph["version"],
            "generation_mode": "mock",
            "tool_mode": "local_draft",
            "graph_id": graph["id"],
            "entrypoint": "graph.py:run",
        }
    }
    (package_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    (package_dir / "graph-design.yaml").write_text(
        yaml.safe_dump({"graph_design": graph}, sort_keys=False),
        encoding="utf-8",
    )
    (package_dir / "tools.yaml").write_text(
        yaml.safe_dump({"tool_requirements": tools}, sort_keys=False),
        encoding="utf-8",
    )
    (package_dir / "README.md").write_text(
        "\n".join(
            [
                f"# {target['agent_target']['name']}",
                "",
                "Local draft agent package generated by the builder.",
                "",
                f"- Target: `{target['agent_target']['id']}`",
                f"- Graph: `{graph['id']}`",
                f"- Version: `{graph['version']}`",
                "- Runtime: `edd_agent_lab.agents.draft_agent.run_draft_agent`",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "graph.py").write_text(
        "\n".join(
            [
                '"""Generated local draft-agent entrypoint."""',
                "",
                "from edd_agent_lab.agents.draft_agent import run_draft_agent",
                "",
                "",
                "def run(*, agent_key, agent_version, target, scenario, graph_design):",
                "    return run_draft_agent(",
                "        agent_key=agent_key,",
                "        agent_version=agent_version,",
                "        target=target,",
                "        scenario=scenario,",
                "        graph_design=graph_design,",
                "    )",
            ]
        ),
        encoding="utf-8",
    )
    return {"path": package_dir, "manifest": manifest, "graph": graph}


def load_draft_target(agent_key: str) -> dict[str, Any] | None:
    path = draft_workspace_dir(agent_key) / "agent-target.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def load_draft_artifacts(agent_key: str) -> dict[str, dict[str, Any]]:
    workspace = draft_workspace_dir(agent_key)
    artifacts: dict[str, dict[str, Any]] = {}
    for artifact_key, filename in DRAFT_ARTIFACT_FILES.items():
        path = workspace / filename
        if not path.is_file():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            artifacts[artifact_key] = data
    return artifacts


def load_draft_artifact_sources(agent_key: str) -> dict[str, str]:
    workspace = draft_workspace_dir(agent_key)
    sources: dict[str, str] = {}
    for artifact_key, filename in DRAFT_ARTIFACT_FILES.items():
        path = workspace / filename
        if path.is_file():
            sources[artifact_key] = path.read_text(encoding="utf-8")
    return sources


def load_draft_artifact_validations(agent_key: str) -> dict[str, dict[str, Any]]:
    artifacts = load_draft_artifacts(agent_key)
    return {
        artifact_key: validate_draft_artifact(artifact_key=artifact_key, data=data)
        for artifact_key, data in artifacts.items()
    }


def validate_draft_artifact(*, artifact_key: str, data: dict[str, Any]) -> dict[str, Any]:
    if artifact_key not in DRAFT_ARTIFACT_FILES:
        raise KeyError(f"Unknown artifact: {artifact_key}")

    errors: list[str] = []
    root_key = DRAFT_ARTIFACT_ROOTS[artifact_key]
    root = data.get(root_key)
    if root is None:
        errors.append(f"Missing top-level `{root_key}` mapping.")
        return {"valid": False, "errors": errors}

    if artifact_key in {
        "behavior_rules",
        "information_requirements",
        "scenario_variants",
        "tool_requirements",
    }:
        if not isinstance(root, list) or not root:
            errors.append(f"`{root_key}` must be a non-empty list.")
            return {"valid": False, "errors": errors}
        required = {
            "behavior_rules": ("id", "description"),
            "information_requirements": ("id", "description"),
            "scenario_variants": ("id", "problem"),
            "tool_requirements": ("id", "suggested_tool_name"),
        }[artifact_key]
        _validate_list_items(root_key=root_key, items=root, required=required, errors=errors)
        return {"valid": not errors, "errors": errors}

    if not isinstance(root, dict):
        errors.append(f"`{root_key}` must be a mapping.")
        return {"valid": False, "errors": errors}

    required_fields = {
        "target": ("id", "name", "purpose", "status"),
        "eval_contract": ("id", "target_id", "metrics"),
        "eval_suite": ("id", "target_id", "checks"),
        "graph_design": ("id", "target_id", "version", "nodes"),
        "graph_design_v1": ("id", "target_id", "version", "nodes"),
        "scenario": ("id", "problem"),
        "v0_run": ("id", "agent", "agent_version", "final_response"),
        "v1_run": ("id", "agent", "agent_version", "final_response"),
        "eval_summary": ("id", "agent", "overall_score", "checks"),
        "eval_summary_v1": ("id", "agent", "overall_score", "checks"),
        "failure_packet": ("id", "agent", "failed_rule"),
        "fix_plan": ("id", "agent", "graph_changes"),
        "comparison": ("id", "agent", "decision"),
        "publish_result": ("id", "agent", "run_id", "status"),
    }[artifact_key]
    _validate_required_fields(
        root_key=root_key,
        payload=root,
        required=required_fields,
        errors=errors,
    )

    list_fields = {
        "eval_contract": ("metrics",),
        "eval_suite": ("checks",),
        "graph_design": ("nodes",),
        "graph_design_v1": ("nodes",),
        "eval_summary": ("checks",),
        "eval_summary_v1": ("checks",),
        "fix_plan": ("graph_changes",),
    }.get(artifact_key, ())
    for field in list_fields:
        if field in root and not isinstance(root[field], list):
            errors.append(f"`{root_key}.{field}` must be a list.")

    return {"valid": not errors, "errors": errors}


def _validate_required_fields(
    *,
    root_key: str,
    payload: dict[str, Any],
    required: tuple[str, ...],
    errors: list[str],
) -> None:
    for field in required:
        value = payload.get(field)
        if value in (None, ""):
            errors.append(f"Missing `{root_key}.{field}`.")


def _validate_list_items(
    *,
    root_key: str,
    items: list[Any],
    required: tuple[str, ...],
    errors: list[str],
) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"`{root_key}[{index}]` must be a mapping.")
            continue
        _validate_required_fields(
            root_key=f"{root_key}[{index}]",
            payload=item,
            required=required,
            errors=errors,
        )


def save_draft_artifact_source(*, agent_key: str, artifact_key: str, source: str) -> None:
    if artifact_key not in DRAFT_ARTIFACT_FILES:
        raise KeyError(f"Unknown artifact: {artifact_key}")
    try:
        data = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid artifact YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Artifact YAML must be a mapping.")
    validation = validate_draft_artifact(artifact_key=artifact_key, data=data)
    if not validation["valid"]:
        raise ValueError(
            "Artifact validation failed: " + "; ".join(str(error) for error in validation["errors"])
        )
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES[artifact_key]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def delete_draft_artifact(*, agent_key: str, artifact_key: str) -> None:
    if artifact_key == "target":
        raise ValueError("Target cannot be deleted from the draft workflow.")
    if artifact_key not in DRAFT_ARTIFACT_FILES:
        raise KeyError(f"Unknown artifact: {artifact_key}")
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES[artifact_key]
    if path.is_file():
        path.unlink()


def delete_draft_workspace(agent_key: str) -> None:
    workspace = draft_workspace_dir(agent_key)
    root = workspace.parent
    if not workspace.is_dir():
        raise FileNotFoundError(f"Draft workspace not found for agent: {agent_key}")
    shutil.rmtree(root)


def archive_draft_workspace(agent_key: str) -> None:
    workspace = draft_workspace_dir(agent_key)
    if not workspace.is_dir():
        raise FileNotFoundError(f"Draft workspace not found for agent: {agent_key}")
    (workspace / ARCHIVE_MARKER_FILE).write_text(
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        encoding="utf-8",
    )


def list_draft_workspaces() -> list[DraftWorkspace]:
    workspaces: list[DraftWorkspace] = []
    for path in sorted(LAB_RUNS_DIR.glob("*/draft")):
        if (path / ARCHIVE_MARKER_FILE).is_file():
            continue
        target_path = path / "agent-target.yaml"
        if not target_path.is_file():
            continue
        data = yaml.safe_load(target_path.read_text(encoding="utf-8")) or {}
        target = data.get("agent_target") or {}
        workspaces.append(
            DraftWorkspace(
                agent_key=path.parent.name.replace("_", "-"),
                name=str(target.get("name") or path.parent.name.replace("_", " ")),
                path=path,
                target_path=target_path,
                updated_at=str(target.get("updated_at") or ""),
            )
        )
    return workspaces
