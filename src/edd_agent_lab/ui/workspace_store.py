"""Local draft agent workspaces for the lab console."""

from __future__ import annotations

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


def load_draft_target(agent_key: str) -> dict[str, Any] | None:
    path = draft_workspace_dir(agent_key) / "agent-target.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


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
