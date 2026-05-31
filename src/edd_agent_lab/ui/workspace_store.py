"""Local draft agent workspaces for the lab console."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

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
    "information_requirements": "information-requirements.yaml",
    "tool_requirements": "tool-requirements.yaml",
    "graph_design": "graph-design.yaml",
    "scenario": "scenario.yaml",
    "v0_run": "v0-run.yaml",
    "eval_summary": "eval-summary.yaml",
    "failure_packet": "failure-packet.yaml",
    "fix_plan": "fix-plan.yaml",
    "graph_design_v1": "graph-design-v1.yaml",
    "v1_run": "v1-run.yaml",
    "eval_summary_v1": "eval-summary-v1.yaml",
    "comparison": "comparison.yaml",
}


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


def save_draft_scenario(*, agent_key: str, problem: str) -> Path:
    target = load_draft_target(agent_key)
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    scenario = build_draft_scenario(agent_key=agent_key, problem=problem)
    path = draft_workspace_dir(agent_key) / DRAFT_ARTIFACT_FILES["scenario"]
    path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    return path


def run_draft_v0(agent_key: str) -> dict[str, Any]:
    target = load_draft_target(agent_key)
    artifacts = load_draft_artifacts(agent_key)
    scenario = artifacts.get("scenario")
    if target is None:
        raise FileNotFoundError(f"Draft target not found for agent: {agent_key}")
    if scenario is None:
        raise FileNotFoundError(f"Draft scenario not found for agent: {agent_key}")

    agent_target = target["agent_target"]
    scenario_data = scenario["scenario"]
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = _draft_v0_response(agent_target=agent_target, scenario=scenario_data)
    run = {
        "run": {
            "id": f"{agent_key}-v0-{now}",
            "agent": agent_key,
            "agent_version": "v0-baseline",
            "generation_mode": "mock",
            "tool_mode": "none",
            "scenario_id": scenario_data["id"],
            "created_at": now,
            "final_response": response,
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
    if run is None:
        raise FileNotFoundError(f"Draft v0 run not found for agent: {agent_key}")
    if eval_contract is None:
        raise FileNotFoundError(f"Draft eval contract not found for agent: {agent_key}")

    checks = [
        {
            "id": "scope_alignment",
            "score": 4.0,
            "passed": True,
            "comment": "The response restates the target and stays within the draft scope.",
        },
        {
            "id": "information_discipline",
            "score": 5.0,
            "passed": True,
            "comment": "The response asks for missing source material before making claims.",
        },
        {
            "id": "action_quality",
            "score": 3.0,
            "passed": False,
            "comment": "The response gives generic setup actions, not domain-specific next steps.",
        },
    ]
    overall_score = round(sum(check["score"] for check in checks) / len(checks), 3)
    summary = {
        "eval_summary": {
            "id": f"{agent_key}-v0-eval",
            "agent": agent_key,
            "agent_version": run["agent_version"],
            "run_id": run["id"],
            "eval_contract_id": eval_contract["id"],
            "overall_score": overall_score,
            "passed": False,
            "checks": checks,
        }
    }
    failure_packet = {
        "failure_packet": {
            "id": f"{agent_key}-v0-action-quality-failure",
            "agent": agent_key,
            "agent_version": run["agent_version"],
            "run_id": run["id"],
            "failed_rule": "recommend_safe_next_actions",
            "observed_behavior": "The v0 baseline recommends generic setup work.",
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


def run_draft_v1(agent_key: str) -> dict[str, Any]:
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

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = _draft_v1_response(
        agent_target=target["agent_target"],
        scenario=scenario["scenario"],
    )
    run = {
        "run": {
            "id": f"{agent_key}-v1-{now}",
            "agent": agent_key,
            "agent_version": graph["version"],
            "generation_mode": "mock",
            "tool_mode": "local_draft",
            "scenario_id": scenario["scenario"]["id"],
            "created_at": now,
            "final_response": response,
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
    if run is None:
        raise FileNotFoundError(f"Draft v1 run not found for agent: {agent_key}")
    if eval_contract is None:
        raise FileNotFoundError(f"Draft eval contract not found for agent: {agent_key}")

    checks = [
        {
            "id": "scope_alignment",
            "score": 4.0,
            "passed": True,
            "comment": "The response stays scoped to the target and scenario.",
        },
        {
            "id": "information_discipline",
            "score": 5.0,
            "passed": True,
            "comment": "The response names missing context before making assumptions.",
        },
        {
            "id": "action_quality",
            "score": 4.0,
            "passed": True,
            "comment": "The response gives safer, scenario-aware next actions.",
        },
    ]
    overall_score = round(sum(check["score"] for check in checks) / len(checks), 3)
    summary = {
        "eval_summary": {
            "id": f"{agent_key}-v1-eval",
            "agent": agent_key,
            "agent_version": run["agent_version"],
            "run_id": run["id"],
            "eval_contract_id": eval_contract["id"],
            "overall_score": overall_score,
            "passed": True,
            "checks": checks,
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
    if v0_eval is None:
        raise FileNotFoundError(f"Draft v0 eval not found for agent: {agent_key}")
    if v1_eval is None:
        raise FileNotFoundError(f"Draft v1 eval not found for agent: {agent_key}")

    delta = round(float(v1_eval["overall_score"]) - float(v0_eval["overall_score"]), 3)
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
            else "Review comparison and publish evidence."
        ),
        "steps": rows,
    }


def draft_artifact_cards(agent_key: str) -> list[dict[str, str]]:
    artifacts = load_draft_artifacts(agent_key)
    definitions = [
        ("target", "Target", "Intent", "Review"),
        ("behavior_rules", "Rules", "Design", "Review"),
        ("eval_contract", "Eval Contract", "Design", "Review"),
        ("information_requirements", "Information", "Design", "Review"),
        ("tool_requirements", "Tools", "Design", "Review blockers"),
        ("graph_design", "v0 Graph", "Build", "Review"),
        ("scenario", "Scenario", "Run", "Edit"),
        ("v0_run", "v0 Run", "Run", "Inspect"),
        ("eval_summary", "v0 Eval", "Evaluate", "Inspect"),
        ("failure_packet", "Failure Packet", "Diagnose", "Review"),
        ("fix_plan", "Fix Plan", "Fix", "Review"),
        ("graph_design_v1", "v1 Graph", "Build", "Inspect"),
        ("v1_run", "v1 Run", "Run", "Inspect"),
        ("eval_summary_v1", "v1 Eval", "Evaluate", "Inspect"),
        ("comparison", "Comparison", "Compare", "Inspect"),
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


def _draft_v0_response(*, agent_target: dict[str, Any], scenario: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {agent_target['name']} v0 baseline",
            "",
            f"**Target purpose:** {agent_target['purpose']}",
            "",
            f"**Scenario:** {scenario['problem']}",
            "",
            "## Initial response",
            "I can help with this, but this draft v0 has no tools or domain evidence wired yet.",
            "Before making a recommendation, I would need the missing source material, "
            "constraints, "
            "and any examples of acceptable output.",
            "",
            "## Safe next actions",
            "- Confirm the user, workflow, and decision this agent should support.",
            "- Add representative scenarios and expected behavior themes.",
            "- Review the generated rules, eval contract, information needs, and tool blockers.",
            "- Run v1 only after the graph design and tool assumptions are explicit.",
        ]
    )


def _draft_v1_response(*, agent_target: dict[str, Any], scenario: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {agent_target['name']} v1 draft",
            "",
            f"**Target purpose:** {agent_target['purpose']}",
            "",
            f"**Scenario:** {scenario['problem']}",
            "",
            "## What I can say now",
            "The request is in scope for this draft agent, but the answer should remain "
            "grounded in source material and constraints that are not fully wired yet.",
            "",
            "## Missing context to collect",
            "- Source material or records the agent should inspect.",
            "- User constraints, risk tolerance, and required output format.",
            "- Examples of acceptable and unacceptable recommendations.",
            "",
            "## Safer next actions",
            "- Gather the missing context before making final recommendations.",
            "- Map each recommendation to a piece of available evidence or an explicit assumption.",
            "- Keep any unsupported claim in an assumptions section.",
            "- Treat missing production tools as a readiness blocker, not as success.",
        ]
    )


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


def list_draft_workspaces() -> list[DraftWorkspace]:
    workspaces: list[DraftWorkspace] = []
    for path in sorted(LAB_RUNS_DIR.glob("*/draft")):
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
