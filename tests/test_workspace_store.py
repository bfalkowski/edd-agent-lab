from __future__ import annotations

from edd_agent_lab.ui.workspace_store import (
    build_target_from_description,
    list_draft_workspaces,
    load_draft_target,
    save_draft_target,
    slugify_agent_name,
)


def test_slugify_agent_name() -> None:
    assert slugify_agent_name("Contract Review Agent") == "contract-review-agent"
    assert slugify_agent_name("  ") == "new-agent"


def test_build_target_from_description_scaffolds_draft() -> None:
    target = build_target_from_description(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )

    payload = target["agent_target"]
    assert payload["id"] == "contract-review-agent-target-v1"
    assert payload["name"] == "Contract Review Agent"
    assert payload["purpose"] == "Help legal teams review risky clauses."
    assert payload["status"] == "draft"
    assert payload["risk_tolerance"] == "needs_review"


def test_save_load_and_list_draft_workspace(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    workspace = save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    loaded = load_draft_target("contract-review-agent")
    workspaces = list_draft_workspaces()

    assert workspace.agent_key == "contract-review-agent"
    assert workspace.target_path.is_file()
    assert loaded is not None
    assert loaded["agent_target"]["name"] == "Contract Review Agent"
    assert loaded["agent_target"]["updated_at"].endswith("Z")
    assert len(workspaces) == 1
    assert workspaces[0].name == "Contract Review Agent"
