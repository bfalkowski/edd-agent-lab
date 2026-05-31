from __future__ import annotations

from edd_agent_lab.ui.workspace_store import (
    build_design_scaffold,
    build_draft_scenario,
    build_target_from_description,
    compare_draft_versions,
    evaluate_draft_v0,
    evaluate_draft_v1,
    generate_draft_fix_plan,
    generate_draft_v1_graph,
    list_draft_workspaces,
    load_draft_artifacts,
    load_draft_target,
    run_draft_v0,
    run_draft_v1,
    save_design_scaffold,
    save_draft_scenario,
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


def test_build_design_scaffold_links_artifacts_to_target() -> None:
    target = build_target_from_description(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    scaffold = build_design_scaffold(target)

    assert scaffold["behavior_rules"]["behavior_rules"][0]["target_id"] == (
        "contract-review-agent-target-v1"
    )
    assert scaffold["eval_contract"]["eval_contract"]["target_id"] == (
        "contract-review-agent-target-v1"
    )
    assert scaffold["graph_design"]["graph_design"]["id"] == "contract-review-agent-graph-v0"


def test_save_design_scaffold_writes_downstream_artifacts(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    paths = save_design_scaffold("contract-review-agent")
    artifacts = load_draft_artifacts("contract-review-agent")

    assert paths["behavior_rules"].is_file()
    assert paths["eval_contract"].is_file()
    assert paths["information_requirements"].is_file()
    assert paths["tool_requirements"].is_file()
    assert paths["graph_design"].is_file()
    assert artifacts["tool_requirements"]["tool_requirements"][0]["production_blocker"] is True


def test_build_draft_scenario() -> None:
    scenario = build_draft_scenario(
        agent_key="contract-review-agent",
        problem="Review this contract for risky payment terms.",
    )

    payload = scenario["scenario"]
    assert payload["id"] == "contract-review-agent-scenario-001"
    assert payload["problem"] == "Review this contract for risky payment terms."
    assert "Ask for missing information" in payload["expected_themes"]


def test_run_draft_v0_writes_local_run_artifacts(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_draft_scenario(
        agent_key="contract-review-agent",
        problem="Review this contract for risky payment terms.",
    )
    run = run_draft_v0("contract-review-agent")
    artifacts = load_draft_artifacts("contract-review-agent")

    assert run["run"]["agent_version"] == "v0-baseline"
    assert run["run"]["generation_mode"] == "mock"
    assert "no tools or domain evidence wired yet" in run["run"]["final_response"]
    assert artifacts["v0_run"]["run"]["scenario_id"] == "contract-review-agent-scenario-001"
    assert (tmp_path / "contract_review_agent" / "draft" / "run-record.json").is_file()


def test_evaluate_draft_v0_writes_summary_and_failure_packet(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_design_scaffold("contract-review-agent")
    save_draft_scenario(
        agent_key="contract-review-agent",
        problem="Review this contract for risky payment terms.",
    )
    run_draft_v0("contract-review-agent")
    summary = evaluate_draft_v0("contract-review-agent")
    artifacts = load_draft_artifacts("contract-review-agent")

    assert summary["eval_summary"]["passed"] is False
    assert summary["eval_summary"]["overall_score"] == 4.0
    assert artifacts["failure_packet"]["failure_packet"]["failed_rule"] == (
        "recommend_safe_next_actions"
    )
    assert (tmp_path / "contract_review_agent" / "draft" / "eval-summary.yaml").is_file()


def test_generate_draft_fix_plan_from_failure_packet(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_design_scaffold("contract-review-agent")
    save_draft_scenario(
        agent_key="contract-review-agent",
        problem="Review this contract for risky payment terms.",
    )
    run_draft_v0("contract-review-agent")
    evaluate_draft_v0("contract-review-agent")
    fix_plan = generate_draft_fix_plan("contract-review-agent")
    artifacts = load_draft_artifacts("contract-review-agent")

    assert fix_plan["fix_plan"]["source_failure_packet_id"] == (
        "contract-review-agent-v0-action-quality-failure"
    )
    assert fix_plan["fix_plan"]["target_version"] == "v1-evidence-aware-actions"
    assert artifacts["fix_plan"]["fix_plan"]["graph_changes"][0]["id"] == (
        "collect_domain_context"
    )
    assert (tmp_path / "contract_review_agent" / "draft" / "fix-plan.yaml").is_file()


def test_draft_v1_run_eval_and_comparison(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_design_scaffold("contract-review-agent")
    save_draft_scenario(
        agent_key="contract-review-agent",
        problem="Review this contract for risky payment terms.",
    )
    run_draft_v0("contract-review-agent")
    evaluate_draft_v0("contract-review-agent")
    generate_draft_fix_plan("contract-review-agent")
    graph = generate_draft_v1_graph("contract-review-agent")
    run = run_draft_v1("contract-review-agent")
    summary = evaluate_draft_v1("contract-review-agent")
    comparison = compare_draft_versions("contract-review-agent")
    artifacts = load_draft_artifacts("contract-review-agent")

    assert graph["graph_design"]["version"] == "v1-evidence-aware-actions"
    assert run["run"]["agent_version"] == "v1-evidence-aware-actions"
    assert summary["eval_summary"]["passed"] is True
    assert comparison["comparison"]["score_delta"] > 0
    assert comparison["comparison"]["decision"] == "candidate_improved"
    assert artifacts["comparison"]["comparison"]["resolved_failures"] == [
        "contract-review-agent-v0-action-quality-failure"
    ]
    assert (tmp_path / "contract_review_agent" / "draft" / "graph-design-v1.yaml").is_file()
