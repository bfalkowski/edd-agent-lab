"""Streamlit reference-scenario workbench for Customer Escalation Triage (doc 12)."""

from __future__ import annotations

import html
from pathlib import Path

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
    draft_artifact_cards,
    draft_comparison_view,
    draft_workflow_status,
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
    update_draft_target,
)

_SESSION_KEYS = (
    "v0_response",
    "v1_response",
    "v0_snapshot",
    "v1_snapshot",
    "last_publish",
    "last_publish_batch",
)

_DRAFT_STEP_LABELS = [
    "Target",
    "Design",
    "Run",
    "Evaluate",
    "Improve",
    "Publish",
]

def _reset_workbench() -> None:
    import streamlit as st

    for key in _SESSION_KEYS:
        st.session_state.pop(key, None)


def _render_console_mode_selector() -> str:
    import streamlit as st

    left, right = st.columns([0.78, 0.22], vertical_alignment="center")
    with left:
        st.markdown(
            """
            <div class="edd-top-mode-label">
              <span>EDD Agent Lab</span>
              <span>Local agent design workspace</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        return str(
            st.selectbox(
                "Console mode",
                ["Start New Agent", "Reference Demo"],
                key="console_mode",
                label_visibility="collapsed",
            )
        )


def _render_start_page() -> None:
    import streamlit as st

    _render_builder_header()

    workspaces = list_draft_workspaces()
    _render_new_agent_panel(expanded=not workspaces)
    if not workspaces:
        _render_empty_draft_state()
        return

    labels = {
        f"{workspace.name} ({workspace.agent_key})": workspace.agent_key
        for workspace in workspaces
    }
    default_agent = st.session_state.get("active_draft_agent") or workspaces[0].agent_key
    agent_keys = list(labels.values())
    default_index = agent_keys.index(default_agent) if default_agent in agent_keys else 0

    rail, main = st.columns([0.28, 0.72], gap="large")
    with rail:
        st.markdown("### Drafts")
        selected_label = st.selectbox(
            "Draft workspace",
            list(labels),
            index=default_index,
            label_visibility="collapsed",
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
    artifacts = load_draft_artifacts(selected_agent)
    status = draft_workflow_status(selected_agent)
    completed = int(status["completed"])
    total = int(status["total"])

    with rail:
        _render_workbench_rail(
            selected_label=selected_label,
            target_path=target_path,
            completed=completed,
            total=total,
            next_action=str(status["next_action"]),
        )
        _render_draft_progress(status)
        _render_workflow_summary(status)

    with main:
        _render_active_draft_header(
            agent_target=agent_target,
            target_path=target_path,
            completed=completed,
            total=total,
            next_action=str(status["next_action"]),
        )
        _render_target_step(selected_agent, agent_target)
        _render_design_step(selected_agent, artifacts, target_path)
        _render_run_step(selected_agent, artifacts, target_path)
        _render_evaluate_step(selected_agent, target_path)
        _render_improve_step(selected_agent, target_path)
        _render_publish_step()


def _render_builder_header() -> None:
    import streamlit as st

    st.markdown(
        """
        <div class="edd-builder-header">
          <div class="edd-builder-kicker">Agent builder</div>
          <div class="edd-builder-title">
            Describe the agent. Shape the loop. Compare the versions.
          </div>
          <div class="edd-builder-subtitle">
            Local developer workspace for turning an idea into EDD artifacts,
            mock runs, eval evidence, and a publishable platform payload.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_new_agent_panel(*, expanded: bool) -> None:
    import streamlit as st

    with st.expander("What agent are we building?", expanded=expanded):
        with st.form("new_agent_form"):
            name = st.text_input("Agent name", placeholder="Contract Review Agent")
            description = st.text_area(
                "Agent idea",
                placeholder=(
                    "I want an agent that helps legal teams review contracts for risky "
                    "clauses, summarize evidence, and recommend safe next actions."
                ),
                height=110,
            )
            submitted = st.form_submit_button("Create draft target", type="primary")

        if submitted:
            clean_name = name.strip()
            clean_description = description.strip()
            if not clean_name or not clean_description:
                st.error("Agent name and purpose are required.")
            else:
                workspace = save_draft_target(
                    name=clean_name,
                    description=clean_description,
                )
                st.session_state.active_draft_agent = workspace.agent_key
                st.success(f"Draft target created for {workspace.name}.")
                st.rerun()


def _render_workbench_rail(
    *,
    selected_label: str,
    target_path: Path,
    completed: int,
    total: int,
    next_action: str,
) -> None:
    import streamlit as st

    st.markdown(
        f"""
        <div class="edd-workbench-rail-card">
          <div class="edd-rail-label">Active draft</div>
          <div class="edd-rail-title">{html.escape(selected_label)}</div>
          <div class="edd-rail-meta">{completed}/{total} steps · local YAML</div>
        </div>
        <div class="edd-rail-next">
          <div class="edd-rail-label">Next</div>
          <div>{html.escape(next_action)}</div>
        </div>
        <div class="edd-rail-path">{html.escape(str(target_path))}</div>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_draft_state() -> None:
    import streamlit as st

    st.markdown(
        """
        <div class="edd-empty-state">
          <div class="edd-empty-title">No local drafts yet</div>
          <div class="edd-empty-text">
            Create a draft target above to start the local EDD loop.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_active_draft_header(
    *,
    agent_target: dict[str, object],
    target_path: Path,
    completed: int,
    total: int,
    next_action: str,
) -> None:
    import streamlit as st

    st.markdown(
        f"""
        <div class="edd-draft-header">
          <div>
            <div class="edd-draft-eyebrow">Local draft workspace</div>
            <div class="edd-draft-title">{html.escape(str(agent_target.get("name", "")))}</div>
            <div class="edd-draft-meta">
              {html.escape(str(agent_target.get("id", "")))} ·
              {status_pill(str(agent_target.get("status", "draft")).upper(), "blue")}
            </div>
          </div>
          <div class="edd-draft-header-stat">
            <div class="edd-draft-stat-value">{completed}/{total}</div>
            <div class="edd-draft-stat-label">steps</div>
          </div>
        </div>
        <div class="edd-draft-subline">
          <strong>Next:</strong> {html.escape(next_action)}
          <span>{html.escape(str(target_path))}</span>
        </div>
        <div class="edd-local-banner">
          Local YAML only · not persisted to platform/Postgres
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_workflow_summary(status: dict[str, object]) -> None:
    import streamlit as st

    rows = []
    for row in status["steps"]:
        state = "complete" if row["complete"] else "pending"
        label = "Done" if row["complete"] else "Pending"
        rows.append(
            f'<div class="edd-workflow-row edd-workflow-row-{state}">'
            f'<span>{html.escape(str(row["step"]))}</span>'
            f'<strong>{label}</strong>'
            '</div>'
        )

    st.markdown(
        f"""
        <div class="edd-workflow-list">
          <div class="edd-rail-label">Workflow</div>
          {"".join(rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_target_step(agent_key: str, agent_target: dict[str, object]) -> None:
    _render_target_editor(agent_key, agent_target)


def _render_design_step(
    agent_key: str,
    artifacts: dict[str, dict[str, object]],
    target_path: Path,
) -> None:
    import streamlit as st
    import yaml

    design_keys = [
        "behavior_rules",
        "eval_contract",
        "information_requirements",
        "tool_requirements",
        "graph_design",
    ]
    ready_count = sum(1 for key in design_keys if key in artifacts)
    design_ready = ready_count == len(design_keys)
    _render_step_panel(
        title="Design artifacts",
        body=(
            "Generate the first pass rules, eval contract, information needs, "
            "tool blockers, and graph design from the target."
        ),
        state="complete" if design_ready else "ready",
        state_label="Complete" if design_ready else "Ready",
    )

    design_cards = [
        card for card in draft_artifact_cards(agent_key) if card["id"] in design_keys
    ]
    _render_artifact_cards(design_cards, title="Design Review")

    ready_count = len(artifacts) - (0 if "target" not in artifacts else 1)
    col_scaffold, col_status = st.columns([1, 2])
    if col_scaffold.button(
        "Scaffold design artifacts",
        type="primary",
        disabled=design_ready,
    ):
        save_design_scaffold(agent_key)
        st.rerun()
    col_status.caption(f"{max(ready_count, 0)} downstream artifacts ready.")

    with st.expander("Artifact YAML", expanded=False):
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


def _render_run_step(
    agent_key: str,
    artifacts: dict[str, dict[str, object]],
    target_path: Path,
) -> None:
    import streamlit as st

    graph_ready = "graph_design" in artifacts
    run = load_draft_artifacts(agent_key).get("v0_run", {}).get("run")
    if not graph_ready:
        _render_step_panel(
            title="First local run",
            body="Scaffold design artifacts before running the deterministic v0 baseline.",
            state="blocked",
            state_label="Blocked",
        )
        return

    _render_step_panel(
        title="First local run",
        body=(
            "Save a first scenario and run the local mock baseline. This creates "
            "the v0 run artifact without calling live model providers."
        ),
        state="complete" if run else "ready",
        state_label="Complete" if run else "Ready",
    )
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
            save_draft_scenario(agent_key=agent_key, problem=clean_problem)
            run_draft_v0(agent_key)
            st.rerun()

    if run:
        st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["v0_run"]))
        _render_run_response(run["final_response"])
        st.caption(
            f"Run `{run['id']}` · mode `{run['generation_mode']}` · "
            f"tool mode `{run['tool_mode']}`"
        )


def _render_evaluate_step(agent_key: str, target_path: Path) -> None:
    import streamlit as st

    latest_artifacts = load_draft_artifacts(agent_key)
    run = latest_artifacts.get("v0_run", {}).get("run")
    if not run:
        st.info("Run v0 before evaluating this draft.")
        return

    if st.button("Evaluate v0", type="primary"):
        evaluate_draft_v0(agent_key)
        st.rerun()

    eval_summary = latest_artifacts.get("eval_summary", {}).get("eval_summary")
    if eval_summary:
        st.markdown("## Local Eval Summary")
        st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["eval_summary"]))
        st.metric("Overall score", f"{eval_summary['overall_score']:.1f} / 5")
        _render_light_table(eval_summary["checks"])
        failure = latest_artifacts.get("failure_packet", {}).get("failure_packet")
        if failure:
            st.warning(
                f"Failure packet: `{failure['id']}` · failed rule "
                f"`{failure['failed_rule']}`"
            )
            st.markdown(f"**Recommended fix:** {failure['recommended_fix']}")
            if st.button("Generate fix plan", type="primary"):
                generate_draft_fix_plan(agent_key)
                st.rerun()


def _render_improve_step(agent_key: str, target_path: Path) -> None:
    import streamlit as st
    import yaml

    latest_artifacts = load_draft_artifacts(agent_key)
    fix_plan = latest_artifacts.get("fix_plan", {}).get("fix_plan")
    if not fix_plan:
        st.info("Generate a fix plan from the v0 failure before creating v1.")
        return

    st.markdown("## Draft Fix Plan")
    st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["fix_plan"]))
    st.markdown(f"**Target version:** `{fix_plan['target_version']}`")
    st.markdown(fix_plan["summary"])
    _render_light_table(fix_plan["graph_changes"])
    with st.expander("Acceptance checks", expanded=False):
        for check in fix_plan["acceptance_checks"]:
            st.markdown(f"- {check}")

    v1_graph = latest_artifacts.get("graph_design_v1", {}).get("graph_design")
    v1_run = latest_artifacts.get("v1_run", {}).get("run")
    v1_eval = latest_artifacts.get("eval_summary_v1", {}).get("eval_summary")
    comparison = latest_artifacts.get("comparison", {}).get("comparison")

    col_graph, col_run, col_eval, col_compare = st.columns(4)
    if col_graph.button("Generate v1 graph"):
        generate_draft_v1_graph(agent_key)
        st.rerun()
    if col_run.button("Run v1", disabled=v1_graph is None):
        run_draft_v1(agent_key)
        st.rerun()
    if col_eval.button("Evaluate v1", disabled=v1_run is None):
        evaluate_draft_v1(agent_key)
        st.rerun()
    if col_compare.button("Compare v0/v1", disabled=v1_eval is None):
        compare_draft_versions(agent_key)
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
        _render_light_table(v1_eval["checks"])
    if comparison:
        st.markdown("## v0/v1 Comparison")
        metric_cols = st.columns(3)
        metric_cols[0].metric("v0", f"{comparison['baseline_score']:.1f} / 5")
        metric_cols[1].metric("v1", f"{comparison['candidate_score']:.1f} / 5")
        metric_cols[2].metric("Delta", f"{comparison['score_delta']:+.1f}")
        comparison_view = draft_comparison_view(agent_key)
        if comparison_view:
            left, right = st.columns(2, gap="medium")
            with left:
                _render_draft_version_panel("v0", comparison_view["v0"])
            with right:
                _render_draft_version_panel("v1", comparison_view["v1"])
            verdict = comparison_view["verdict"]
            st.markdown("## Draft EDD Verdict")
            st.success(f"{verdict['decision']}: {verdict['summary']}")
            st.markdown(f"**What failed:** {verdict['what_failed']}")
            st.markdown(f"**What changed:** {verdict['what_changed']}")
            st.warning(f"Remaining blocker: {verdict['remaining_blocker']}")


def _render_publish_step() -> None:
    import streamlit as st

    st.markdown("## Publish")
    st.info(
        "Greenfield publish is not wired yet. The current draft artifacts remain local "
        "until the platform persistence boundary is implemented."
    )


def _render_step_panel(
    *,
    title: str,
    body: str,
    state: str,
    state_label: str,
) -> None:
    import streamlit as st

    pill_status = {
        "complete": "green",
        "ready": "blue",
        "blocked": "yellow",
        "failed": "red",
    }.get(state, "blue")
    st.markdown(
        f"""
        <div class="edd-step-panel edd-step-panel-{html.escape(state)}">
          <div>
            <div class="edd-step-panel-title">{html.escape(title)}</div>
            <div class="edd-step-panel-body">{html.escape(body)}</div>
          </div>
          <div>{status_pill(state_label.upper(), pill_status)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_run_response(response: str) -> None:
    import streamlit as st

    response_html = html.escape(response).replace("\n", "<br/>")
    st.markdown(
        f"""
        <div class="edd-run-response">
          {response_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_light_table(rows: list[dict[str, object]]) -> None:
    import streamlit as st

    if not rows:
        return
    columns = list(rows[0].keys())
    header = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    body_rows = []
    for row in rows:
        cells = "".join(
            f"<td>{html.escape(_format_table_cell(row.get(column)))}</td>"
            for column in columns
        )
        body_rows.append(f"<tr>{cells}</tr>")
    st.markdown(
        f"""
        <table class="edd-light-table">
          <thead><tr>{header}</tr></thead>
          <tbody>{"".join(body_rows)}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _format_table_cell(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _render_draft_version_panel(label: str, panel: dict[str, object]) -> None:
    import streamlit as st

    passed = bool(panel["passed"])
    pill = status_pill("PASS" if passed else "FAIL", "green" if passed else "red")
    st.markdown(f"### {label}: `{panel['version']}`")
    st.markdown(
        f"Score: **{float(panel['score']):.1f} / 5** · {pill} · "
        f"Tool mode: `{panel['tool_mode']}`",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(str(panel["response"]))
    if passed:
        st.success(str(panel["callout"]))
    else:
        st.error(str(panel["callout"]))


def _render_target_editor(agent_key: str, agent_target: dict[str, object]) -> None:
    import streamlit as st

    with st.expander("Edit target", expanded=False):
        with st.form(f"edit_target_{agent_key}"):
            name = st.text_input("Target name", value=str(agent_target.get("name", "")))
            purpose = st.text_area(
                "Purpose",
                value=str(agent_target.get("purpose", "")),
                height=120,
            )
            risk_tolerance = st.text_input(
                "Risk tolerance",
                value=str(agent_target.get("risk_tolerance", "needs_review")),
            )
            output_format = st.text_input(
                "Expected output format",
                value=str(agent_target.get("expected_output_format", "needs_review")),
            )
            submitted = st.form_submit_button("Save target changes")
        if submitted:
            try:
                update_draft_target(
                    agent_key=agent_key,
                    name=name,
                    purpose=purpose,
                    risk_tolerance=risk_tolerance,
                    expected_output_format=output_format,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Target updated.")
                st.rerun()


def _render_artifact_cards(cards: list[dict[str, str]], title: str = "Artifact Review") -> None:
    import streamlit as st

    st.markdown(f"## {title}")
    rows = []
    for card in cards:
        status = card["status"]
        pill = status_pill(status.upper(), "green" if status == "ready" else "blue")
        rows.append(
            f'<div class="edd-artifact-row">'
            '<div>'
            f'<div class="edd-artifact-title">{html.escape(card["artifact"])}</div>'
            f'<div class="edd-artifact-meta">{html.escape(card["group"])} · '
            f'{html.escape(card["action"])}</div>'
            '</div>'
            f'<code>{html.escape(card["file"])}</code>'
            f'<div>{pill}</div>'
            '</div>'
        )
    st.markdown(
        f'<div class="edd-artifact-list">{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def _render_draft_progress(status: dict[str, object]) -> None:
    import streamlit as st

    completed = int(status["completed"])
    total = int(status["total"])
    st.progress(float(status["percent"]), text=f"{completed} of {total} steps complete")


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
        sidebar_brand()
        st.divider()
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
    mode = _render_console_mode_selector()

    if mode == "Start New Agent":
        _render_start_page()
    else:
        platform_health = check_platform_health()
        _render_reference_workbench(platform_health)


if __name__ == "__main__":
    main()
