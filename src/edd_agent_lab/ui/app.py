"""Streamlit reference-scenario workbench for Customer Escalation Triage (doc 12)."""

from __future__ import annotations

import html

from dotenv import load_dotenv

from edd_agent_lab.ui.layout import load_css, page_shell, sidebar_brand, status_pill
from edd_agent_lab.ui.reference_core import (
    AGENT_KEY,
    SCENARIO_ID,
    V0,
    V1,
    check_platform_health,
    platform_console_url,
)
from edd_agent_lab.ui.workbench import snapshot_from_state
from edd_agent_lab.ui.workbench_views import (
    render_context_bar,
    render_details_tabs,
    render_edd_verdict,
    render_scenario_summary,
    render_version_panel_doc12,
    run_compare_workflow,
    run_v0_workflow,
    run_v1_workflow,
)
from edd_agent_lab.ui.workspace_store import (
    DRAFT_ARTIFACT_FILES,
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
)

_SESSION_KEYS = (
    "v0_response",
    "v1_response",
    "v0_snapshot",
    "v1_snapshot",
    "last_publish",
    "last_publish_batch",
)


def _reset_workbench() -> None:
    import streamlit as st

    for key in _SESSION_KEYS:
        st.session_state.pop(key, None)


def _render_start_page() -> None:
    import streamlit as st
    import yaml

    page_shell(
        "EDD Agent Lab",
        "Start with intent, create local design artifacts, then run and compare versions.",
    )

    st.markdown(
        """
        <div class="edd-card">
          <div class="edd-card-title">Create a new agent draft</div>
          <div class="edd-card-subtitle">
            This first slice creates the root target artifact locally. Rules, evals,
            requirements, graph design, and v0 runs build from this target next.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("new_agent_form"):
        name = st.text_input("Agent name", placeholder="Contract Review Agent")
        description = st.text_area(
            "Agent purpose",
            placeholder=(
                "I want an agent that helps legal teams review contracts for risky "
                "clauses, summarize evidence, and recommend safe next actions."
            ),
            height=150,
        )
        submitted = st.form_submit_button("Create draft target", type="primary")

    if submitted:
        clean_name = name.strip()
        clean_description = description.strip()
        if not clean_name or not clean_description:
            st.error("Agent name and purpose are required.")
        else:
            workspace = save_draft_target(name=clean_name, description=clean_description)
            st.session_state.active_draft_agent = workspace.agent_key
            st.success(f"Draft target created for {workspace.name}.")

    workspaces = list_draft_workspaces()
    if not workspaces:
        st.info("No local draft agents yet.")
        return

    st.markdown("## Local Drafts")
    labels = {
        f"{workspace.name} ({workspace.agent_key})": workspace.agent_key
        for workspace in workspaces
    }
    default_agent = st.session_state.get("active_draft_agent") or workspaces[0].agent_key
    agent_keys = list(labels.values())
    default_index = agent_keys.index(default_agent) if default_agent in agent_keys else 0
    selected_label = st.selectbox(
        "Draft workspace",
        list(labels),
        index=default_index,
    )
    selected_agent = labels[selected_label]
    st.session_state.active_draft_agent = selected_agent
    target = load_draft_target(selected_agent)
    if not target:
        st.warning("Draft target file is missing.")
        return

    target_path = next(
        workspace.target_path for workspace in workspaces if workspace.agent_key == selected_agent
    )
    agent_target = target.get("agent_target") or {}
    st.markdown(
        f"""
        <div class="edd-card">
          <div class="edd-card-title">{html.escape(str(agent_target.get("name", "")))}</div>
          <div class="edd-card-subtitle">
            Target: {html.escape(str(agent_target.get("id", "")))} ·
            Status: {status_pill(str(agent_target.get("status", "draft")).upper(), "blue")}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(str(target_path))
    artifacts = load_draft_artifacts(selected_agent)
    ready_count = len(artifacts) - (0 if "target" not in artifacts else 1)
    col_scaffold, col_status = st.columns([1, 2])
    if col_scaffold.button("Scaffold design artifacts", type="primary"):
        save_design_scaffold(selected_agent)
        st.rerun()
    col_status.caption(f"{max(ready_count, 0)} downstream artifacts ready.")

    display_order = [
        ("target", "Target"),
        ("behavior_rules", "Rules"),
        ("eval_contract", "Eval Contract"),
        ("information_requirements", "Information"),
        ("tool_requirements", "Tools"),
        ("graph_design", "Graph"),
    ]
    tabs = st.tabs([label for _, label in display_order])
    for tab, (artifact_key, _label) in zip(tabs, display_order, strict=True):
        with tab:
            payload = artifacts.get(artifact_key)
            if payload is None:
                filename = DRAFT_ARTIFACT_FILES[artifact_key]
                st.info(f"{filename} has not been generated yet.")
                continue
            st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES[artifact_key]))
            st.code(yaml.safe_dump(payload, sort_keys=False), language="yaml")

    st.markdown("## First Local Run")
    scenario = artifacts.get("scenario", {}).get("scenario", {})
    default_problem = str(
        scenario.get("problem")
        or "Describe the first task this draft agent should handle."
    )
    with st.form("draft_scenario_form"):
        problem = st.text_area("Test scenario", value=default_problem, height=130)
        run_submitted = st.form_submit_button("Save scenario and run v0", type="primary")
    if run_submitted:
        clean_problem = problem.strip()
        if not clean_problem:
            st.error("A test scenario is required before running v0.")
        else:
            save_draft_scenario(agent_key=selected_agent, problem=clean_problem)
            run_draft_v0(selected_agent)
            st.rerun()

    run = load_draft_artifacts(selected_agent).get("v0_run", {}).get("run")
    if run:
        st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["v0_run"]))
        st.markdown(run["final_response"])
        st.caption(
            f"Run `{run['id']}` · mode `{run['generation_mode']}` · "
            f"tool mode `{run['tool_mode']}`"
        )
        if st.button("Evaluate v0", type="primary"):
            evaluate_draft_v0(selected_agent)
            st.rerun()

    latest_artifacts = load_draft_artifacts(selected_agent)
    eval_summary = latest_artifacts.get("eval_summary", {}).get("eval_summary")
    if eval_summary:
        st.markdown("## Local Eval Summary")
        st.metric("Overall score", f"{eval_summary['overall_score']:.1f} / 5")
        st.dataframe(eval_summary["checks"], use_container_width=True, hide_index=True)
        failure = latest_artifacts.get("failure_packet", {}).get("failure_packet")
        if failure:
            st.warning(
                f"Failure packet: `{failure['id']}` · failed rule "
                f"`{failure['failed_rule']}`"
            )
            st.markdown(f"**Recommended fix:** {failure['recommended_fix']}")
            if st.button("Generate fix plan", type="primary"):
                generate_draft_fix_plan(selected_agent)
                st.rerun()

    fix_plan = latest_artifacts.get("fix_plan", {}).get("fix_plan")
    if fix_plan:
        st.markdown("## Draft Fix Plan")
        st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["fix_plan"]))
        st.markdown(f"**Target version:** `{fix_plan['target_version']}`")
        st.markdown(fix_plan["summary"])
        st.dataframe(fix_plan["graph_changes"], use_container_width=True, hide_index=True)
        with st.expander("Acceptance checks", expanded=False):
            for check in fix_plan["acceptance_checks"]:
                st.markdown(f"- {check}")

        v1_graph = latest_artifacts.get("graph_design_v1", {}).get("graph_design")
        v1_run = latest_artifacts.get("v1_run", {}).get("run")
        v1_eval = latest_artifacts.get("eval_summary_v1", {}).get("eval_summary")
        comparison = latest_artifacts.get("comparison", {}).get("comparison")

        col_graph, col_run, col_eval, col_compare = st.columns(4)
        if col_graph.button("Generate v1 graph"):
            generate_draft_v1_graph(selected_agent)
            st.rerun()
        if col_run.button("Run v1", disabled=v1_graph is None):
            run_draft_v1(selected_agent)
            st.rerun()
        if col_eval.button("Evaluate v1", disabled=v1_run is None):
            evaluate_draft_v1(selected_agent)
            st.rerun()
        if col_compare.button("Compare v0/v1", disabled=v1_eval is None):
            compare_draft_versions(selected_agent)
            st.rerun()

        if v1_graph:
            with st.expander("v1 graph design", expanded=False):
                st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["graph_design_v1"]))
                st.code(
                    yaml.safe_dump({"graph_design": v1_graph}, sort_keys=False),
                    language="yaml",
                )
        if v1_run:
            st.markdown("## v1 Local Run")
            st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["v1_run"]))
            st.markdown(v1_run["final_response"])
            st.caption(
                f"Run `{v1_run['id']}` · mode `{v1_run['generation_mode']}` · "
                f"tool mode `{v1_run['tool_mode']}`"
            )
        if v1_eval:
            st.markdown("## v1 Eval Summary")
            st.metric("v1 overall score", f"{v1_eval['overall_score']:.1f} / 5")
            st.dataframe(v1_eval["checks"], use_container_width=True, hide_index=True)
        if comparison:
            st.markdown("## v0/v1 Comparison")
            metric_cols = st.columns(3)
            metric_cols[0].metric("v0", f"{comparison['baseline_score']:.1f} / 5")
            metric_cols[1].metric("v1", f"{comparison['candidate_score']:.1f} / 5")
            metric_cols[2].metric("Delta", f"{comparison['score_delta']:+.1f}")
            st.success(f"{comparison['decision']}: {comparison['summary']}")


def _render_reference_workbench(platform_health: dict[str, object]) -> None:
    import streamlit as st

    from edd_agent_lab.integrations.reference_publish import load_reference_publish_artifacts
    from edd_agent_lab.scenarios.loading import load_scenario
    from edd_agent_lab.ui.reference_data import load_graph_design_bundle

    artifacts = load_reference_publish_artifacts()
    scenario = load_scenario(AGENT_KEY, SCENARIO_ID)
    failure = artifacts["failure_packet"]
    v0_design, _ = load_graph_design_bundle("v0")
    v1_design, _ = load_graph_design_bundle("v1")

    with st.sidebar:
        st.markdown("### Workbench")
        st.button(
            "Reset workbench",
            use_container_width=True,
            on_click=_reset_workbench,
            help="Clear triage outputs and eval snapshots.",
        )

        st.divider()
        st.markdown("### Platform")
        if platform_health.get("reachable"):
            st.markdown(
                f"{status_pill('API reachable', 'green')}",
                unsafe_allow_html=True,
            )
            st.caption(str(platform_health.get("api_base")))
        elif platform_health.get("configured"):
            st.markdown(
                f"{status_pill('API unreachable', 'yellow')}",
                unsafe_allow_html=True,
            )
            st.caption(str(platform_health.get("message")))
        else:
            st.caption("Set `EDD_API_BASE_URL` to enable publish.")

        st.markdown(
            f"[Overview]({platform_console_url('overview')}) · "
            f"[Failure]({platform_console_url('failure_packets')}) · "
            f"[Compare]({platform_console_url('compare_versions')})"
        )
        st.caption("Platform console :8501 · Lab workbench :8502")

    page_shell(
        "Customer Escalation Triage",
        "Reference workbench — v0 guessed, v1 checked evidence.",
    )

    render_context_bar(
        artifacts=artifacts,
        scenario_title=scenario.title,
        platform_health=platform_health,
        on_run_v0=lambda: run_v0_workflow(st),
        on_run_v1=lambda: run_v1_workflow(st),
        on_compare=lambda: run_compare_workflow(st),
        on_refresh=lambda: st.rerun(),
    )

    render_scenario_summary(
        title=scenario.title,
        problem=scenario.problem,
        expected_themes=list(scenario.expected_themes or []),
    )

    v0_response = st.session_state.get("v0_response")
    v1_response = st.session_state.get("v1_response")
    v0_snapshot = snapshot_from_state(st, "v0_snapshot")
    v1_snapshot = snapshot_from_state(st, "v1_snapshot")

    left_col, right_col = st.columns(2, gap="medium")
    with left_col:
        render_version_panel_doc12(
            version=V0,
            response=v0_response,
            snapshot=v0_snapshot,
            artifacts=artifacts,
            graph_summary=v0_design.get("name") or "single_pass_response",
            tool_mode="fixture",
            callout=(
                f"Failed `{failure['failed_rule']}`. "
                "The agent overclaimed root cause without enough evidence."
            ),
            callout_pill="red",
        )
    with right_col:
        gate = artifacts["gate_result"]
        render_version_panel_doc12(
            version=V1,
            response=v1_response,
            snapshot=v1_snapshot,
            artifacts=artifacts,
            graph_summary=v1_design.get("name") or "evidence_triage_v1",
            tool_mode="mock_local",
            production_status=str(gate.get("production_readiness_status", "blocked")).upper(),
            callout=(
                "Uses Facts / Hypotheses / Unknowns, evidence collection, "
                "and a customer-safe update review."
            ),
            callout_pill="green",
        )

    render_edd_verdict(artifacts=artifacts)
    render_details_tabs(artifacts=artifacts, platform_health=platform_health)


def main() -> None:
    import streamlit as st

    load_dotenv()
    st.set_page_config(
        page_title="EDD Agent Lab",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_css()
    sidebar_brand()

    platform_health = check_platform_health()

    with st.sidebar:
        st.markdown("### Mode")
        mode = st.radio(
            "Console mode",
            ["Start New Agent", "Reference Demo"],
            label_visibility="collapsed",
        )

    if mode == "Start New Agent":
        _render_start_page()
    else:
        _render_reference_workbench(platform_health)


if __name__ == "__main__":
    main()
