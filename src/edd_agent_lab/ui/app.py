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
    list_draft_workspaces,
    load_draft_target,
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
    st.code(yaml.safe_dump(target, sort_keys=False), language="yaml")


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
