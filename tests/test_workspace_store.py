from __future__ import annotations

from types import SimpleNamespace

import pytest

from edd_agent_lab.integrations.edd_client import QueuedEDDClient
from edd_agent_lab.ui.workspace_store import (
    build_design_scaffold,
    build_draft_scenario,
    build_target_from_description,
    compare_draft_versions,
    draft_artifact_cards,
    draft_comparison_view,
    draft_workflow_status,
    evaluate_draft_v0,
    evaluate_draft_v1,
    generate_draft_agent_package,
    generate_draft_fix_plan,
    generate_draft_v1_graph,
    list_draft_workspaces,
    load_draft_artifact_validations,
    load_draft_artifacts,
    load_draft_target,
    publish_draft_evidence,
    run_draft_v0,
    run_draft_v1,
    save_design_scaffold,
    save_draft_artifact_source,
    save_draft_scenario,
    save_draft_target,
    slugify_agent_name,
    update_draft_target,
    validate_draft_artifact,
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


def test_update_draft_target_edits_existing_workspace(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    updated = update_draft_target(
        agent_key="contract-review-agent",
        name="Contract Risk Review Agent",
        purpose="Review contract clauses and surface negotiation risks.",
        risk_tolerance="low",
        expected_output_format="risk summary",
    )
    loaded = load_draft_target("contract-review-agent")

    assert updated["agent_target"]["name"] == "Contract Risk Review Agent"
    assert loaded is not None
    assert loaded["agent_target"]["purpose"] == (
        "Review contract clauses and surface negotiation risks."
    )
    assert loaded["agent_target"]["risk_tolerance"] == "low"
    assert loaded["agent_target"]["expected_output_format"] == "risk summary"


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
    assert scaffold["eval_suite"]["eval_suite"]["contract_id"] == (
        "contract-review-agent-eval-contract-v1"
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
    assert paths["eval_suite"].is_file()
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
    assert run["run"]["tool_mode"] == "local_draft"
    assert run["run"]["node_trace"] == [
        "understand_request: scoped to Help legal teams review risky clauses.",
        "draft_response",
    ]
    assert "no tools or domain evidence wired yet" in run["run"]["final_response"]
    assert artifacts["v0_run"]["run"]["scenario_id"] == "contract-review-agent-scenario-001"
    assert (tmp_path / "contract_review_agent" / "draft" / "run-record.json").is_file()
    assert (tmp_path / "contract_review_agent" / "agent" / "manifest.yaml").is_file()


def test_run_draft_v0_uses_live_generation_when_enabled(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.agents import draft_agent
    from edd_agent_lab.ui import workspace_store

    class FakeChatModel:
        def invoke(self, messages):
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            return SimpleNamespace(
                content=(
                    "## What I can say now\n"
                    "Live response grounded in the provided target and scenario.\n\n"
                    "## Missing context to collect\n"
                    "- Source material.\n\n"
                    "## Safe next actions\n"
                    "- Map recommendations to available evidence."
                )
            )

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    monkeypatch.setenv("AGENT_GENERATION_MODE", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(draft_agent, "get_chat_model", lambda temperature=0.2: FakeChatModel())

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_draft_scenario(
        agent_key="contract-review-agent",
        problem="Review this contract for risky payment terms.",
    )
    run = run_draft_v0("contract-review-agent")

    assert run["run"]["generation_mode"] == "live"
    assert run["run"]["node_trace"] == [
        "understand_request: scoped to Help legal teams review risky clauses.",
        "draft_response: live",
    ]
    assert "Live response grounded" in run["run"]["final_response"]


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
    assert summary["eval_summary"]["eval_suite_id"] == "contract-review-agent-eval-suite-v1"
    assert summary["eval_summary"]["rule_results"] == [
        {
            "rule_id": "ask_for_missing_information",
            "passed": True,
            "checks": ["information_discipline"],
        },
        {
            "rule_id": "recommend_safe_next_actions",
            "passed": False,
            "checks": ["action_quality"],
        },
        {
            "rule_id": "state_purpose_and_scope",
            "passed": True,
            "checks": ["scope_alignment"],
        },
    ]
    assert artifacts["failure_packet"]["failure_packet"]["failed_rule"] == (
        "recommend_safe_next_actions"
    )
    assert artifacts["failure_packet"]["failure_packet"]["failures"][0]["metric_id"] == (
        "action_quality"
    )
    assert (tmp_path / "contract_review_agent" / "draft" / "eval-summary.yaml").is_file()


def test_evaluate_live_draft_uses_hybrid_judge(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.agents import draft_agent
    from edd_agent_lab.evals.scoring import CheckScore
    from edd_agent_lab.ui import workspace_store

    class FakeChatModel:
        def invoke(self, _messages):
            return SimpleNamespace(
                content=(
                    "Target purpose and scenario are clear. Missing context includes source "
                    "material. Safe next actions use available evidence, explicit assumption, "
                    "and readiness blocker."
                )
            )

    def fake_score_check(check, _response_text):
        return CheckScore(
            id=check.id,
            score=0.8,
            passed=True,
            comment="llm judge passed",
            weight=check.weight,
            method="llm_judge",
        )

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    monkeypatch.setenv("AGENT_GENERATION_MODE", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(draft_agent, "get_chat_model", lambda temperature=0.2: FakeChatModel())
    monkeypatch.setattr(workspace_store, "score_check", fake_score_check)

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

    assert summary["eval_summary"]["judge_mode"] == "hybrid"
    assert all(check["method"] == "hybrid" for check in summary["eval_summary"]["checks"])
    assert summary["eval_summary"]["checks"][0]["llm_score"] == 4.0


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
    assert run["run"]["node_trace"] == [
        "understand_request: scoped to Help legal teams review risky clauses.",
        "collect_domain_context",
        "plan_grounded_next_actions",
        "draft_response",
    ]
    assert summary["eval_summary"]["passed"] is True
    assert comparison["comparison"]["score_delta"] > 0
    assert comparison["comparison"]["decision"] == "candidate_improved"
    assert artifacts["comparison"]["comparison"]["resolved_failures"] == [
        "contract-review-agent-v0-action-quality-failure"
    ]
    assert (tmp_path / "contract_review_agent" / "draft" / "graph-design-v1.yaml").is_file()


def test_publish_draft_evidence_writes_publish_result(tmp_path, monkeypatch) -> None:
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
    generate_draft_v1_graph("contract-review-agent")
    run_draft_v1("contract-review-agent")
    evaluate_draft_v1("contract-review-agent")
    compare_draft_versions("contract-review-agent")

    result = publish_draft_evidence(
        "contract-review-agent",
        client=QueuedEDDClient(queue_dir=tmp_path / "queue"),
    )
    artifacts = load_draft_artifacts("contract-review-agent")

    publish_result = result["publish_result"]
    assert publish_result["status"] == "queued"
    assert publish_result["run_id"] == (
        "contract-review-agent-v1-evidence-aware-actions-publish"
    )
    assert publish_result["publish_envelope"]["publish_schema_version"] == "2"
    assert publish_result["publish_envelope"]["target"]["id"] == (
        "contract-review-agent-target-v1"
    )
    assert artifacts["publish_result"]["publish_result"]["queue_path"].endswith(".json")
    assert (tmp_path / "contract_review_agent" / "draft" / "publish-result.yaml").is_file()


def test_generate_draft_agent_package_writes_manifest_graph_and_tools(
    tmp_path, monkeypatch
) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_design_scaffold("contract-review-agent")
    package = generate_draft_agent_package("contract-review-agent")

    package_dir = tmp_path / "contract_review_agent" / "agent"
    assert package["manifest"]["agent"]["entrypoint"] == "graph.py:run"
    assert package["manifest"]["agent"]["tool_mode"] == "local_draft"
    assert package_dir.joinpath("manifest.yaml").is_file()
    assert package_dir.joinpath("graph.py").is_file()
    assert package_dir.joinpath("graph-design.yaml").is_file()
    assert package_dir.joinpath("tools.yaml").is_file()


def test_draft_comparison_view_summarizes_versions_and_verdict(tmp_path, monkeypatch) -> None:
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
    generate_draft_v1_graph("contract-review-agent")
    run_draft_v1("contract-review-agent")
    evaluate_draft_v1("contract-review-agent")
    compare_draft_versions("contract-review-agent")
    view = draft_comparison_view("contract-review-agent")

    assert view["v0"]["version"] == "v0-baseline"
    assert view["v0"]["passed"] is False
    assert view["v1"]["version"] == "v1-evidence-aware-actions"
    assert view["v1"]["passed"] is True
    assert view["verdict"]["decision"] == "candidate_improved"
    assert view["verdict"]["remaining_blocker"] == (
        "Draft tools are local placeholders, not production connectors."
    )


def test_draft_workflow_status_reports_next_action(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    initial = draft_workflow_status("contract-review-agent")
    save_design_scaffold("contract-review-agent")
    scaffolded = draft_workflow_status("contract-review-agent")

    assert initial["completed"] == 1
    assert initial["total"] == 11
    assert initial["next_action"] == "Scaffold rules, eval, requirements, and graph."
    assert scaffolded["completed"] == 2
    assert scaffolded["next_action"] == "Add a first local test scenario."


def test_draft_artifact_cards_report_ready_and_pending(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_design_scaffold("contract-review-agent")
    cards = draft_artifact_cards("contract-review-agent")
    by_id = {card["id"]: card for card in cards}

    assert by_id["target"]["status"] == "ready"
    assert by_id["behavior_rules"]["status"] == "ready"
    assert by_id["eval_suite"]["status"] == "ready"
    assert by_id["scenario"]["status"] == "pending"
    assert by_id["publish_result"]["file"] == "publish-result.yaml"
    assert by_id["comparison"]["file"] == "comparison.yaml"


def test_delete_draft_workspace_removes_project(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )

    assert workspace_store.draft_workspace_dir("contract-review-agent").is_dir()

    workspace_store.delete_draft_workspace("contract-review-agent")

    assert workspace_store.list_draft_workspaces() == []
    assert not (tmp_path / "contract_review_agent").exists()


def test_save_draft_artifact_source_reports_invalid_yaml(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )

    with pytest.raises(ValueError, match="Invalid artifact YAML"):
        save_draft_artifact_source(
            agent_key="contract-review-agent",
            artifact_key="scenario",
            source="scenario: [unterminated",
        )


def test_validate_draft_artifact_reports_missing_required_fields() -> None:
    validation = validate_draft_artifact(
        artifact_key="target",
        data={"agent_target": {"id": "contract-review-agent-target-v1"}},
    )

    assert validation == {
        "valid": False,
        "errors": [
            "Missing `agent_target.name`.",
            "Missing `agent_target.purpose`.",
            "Missing `agent_target.status`.",
        ],
    }


def test_save_draft_artifact_source_rejects_invalid_shape(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )

    with pytest.raises(ValueError, match="Artifact validation failed"):
        save_draft_artifact_source(
            agent_key="contract-review-agent",
            artifact_key="target",
            source="agent_target:\n  id: contract-review-agent-target-v1\n",
        )


def test_load_draft_artifact_validations_reports_existing_artifacts(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)

    save_draft_target(
        name="Contract Review Agent",
        description="Help legal teams review risky clauses.",
    )
    save_design_scaffold("contract-review-agent")

    validations = load_draft_artifact_validations("contract-review-agent")

    assert validations["target"]["valid"] is True
    assert validations["behavior_rules"]["valid"] is True
    assert validations["eval_suite"]["valid"] is True
