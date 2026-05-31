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
