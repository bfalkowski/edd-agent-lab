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

_DRAFT_STEP_ARTIFACTS = {
    "Target": ["target"],
    "Design": [
        "behavior_rules",
        "eval_contract",
        "information_requirements",
        "tool_requirements",
        "graph_design",
    ],
    "Run": ["scenario", "v0_run"],
    "Evaluate": ["eval_summary", "failure_packet", "fix_plan"],
    "Improve": ["graph_design_v1", "v1_run", "eval_summary_v1", "comparison"],
    "Publish": [],
}


def _reset_workbench() -> None:
    import streamlit as st

    for key in _SESSION_KEYS:
        st.session_state.pop(key, None)


def _render_start_page() -> None:
    import streamlit as st

    page_shell(
        "EDD Agent Lab",
        "Start with intent, create local design artifacts, then run and compare versions.",
    )

    workspaces = list_draft_workspaces()
    _render_new_agent_panel(expanded=not workspaces)
    if not workspaces:
        _render_empty_draft_state()
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
    artifacts = load_draft_artifacts(selected_agent)
    status = draft_workflow_status(selected_agent)
    completed = int(status["completed"])
    total = int(status["total"])
    _render_active_draft_header(
        agent_target=agent_target,
        target_path=target_path,
        completed=completed,
        total=total,
        next_action=str(status["next_action"]),
    )
    _render_draft_progress(status)

    selected_step = _draft_step_selector(selected_agent, status)
    if selected_step == "Target":
        _render_target_step(selected_agent, agent_target)
    elif selected_step == "Design":
        _render_design_step(selected_agent, artifacts, target_path)
    elif selected_step == "Run":
        _render_run_step(selected_agent, artifacts, target_path)
    elif selected_step == "Evaluate":
        _render_evaluate_step(selected_agent, target_path)
    elif selected_step == "Improve":
        _render_improve_step(selected_agent, target_path)
    else:
        _render_publish_step()


def _render_new_agent_panel(*, expanded: bool) -> None:
    import streamlit as st

    with st.expander("Create a new agent draft", expanded=expanded):
        st.caption(
            "Creates the root target artifact locally. Rules, evals, requirements, "
            "graph design, and runs build from this target."
        )
        with st.form("new_agent_form"):
            name = st.text_input("Agent name", placeholder="Contract Review Agent")
            description = st.text_area(
                "Agent purpose",
                placeholder=(
                    "I want an agent that helps legal teams review contracts for risky "
                    "clauses, summarize evidence, and recommend safe next actions."
                ),
                height=130,
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


def _draft_step_selector(agent_key: str, status: dict[str, object]) -> str:
    import streamlit as st

    default_step = _default_draft_step(status)
    session_key = f"draft_step_{agent_key}"
    if st.session_state.get(session_key) not in _DRAFT_STEP_LABELS:
        st.session_state[session_key] = default_step

    selected_step = st.segmented_control(
        "Workflow step",
        _DRAFT_STEP_LABELS,
        default=st.session_state[session_key],
        key=session_key,
        label_visibility="collapsed",
        width="stretch",
    )
    selected_label = str(selected_step or default_step)
    _render_draft_stepper(selected_label, status)
    return selected_label


def _default_draft_step(status: dict[str, object]) -> str:
    first_pending = next(
        (row["id"] for row in status["steps"] if not row["complete"]),
        None,
    )
    if first_pending is None:
        return "Publish"
    if first_pending in {"target"}:
        return "Target"
    if first_pending in {
        "behavior_rules",
        "eval_contract",
        "information_requirements",
        "tool_requirements",
        "graph_design",
    }:
        return "Design"
    if first_pending in {"scenario", "v0_run"}:
        return "Run"
    if first_pending in {"eval_summary", "failure_packet", "fix_plan"}:
        return "Evaluate"
    if first_pending in {"graph_design_v1", "v1_run", "eval_summary_v1", "comparison"}:
        return "Improve"
    return "Publish"


def _render_draft_stepper(selected_step: str, status: dict[str, object]) -> None:
    import streamlit as st

    completed_ids = {
        str(row["id"]) for row in status["steps"] if bool(row["complete"])
    }
    tiles = []
    for index, label in enumerate(_DRAFT_STEP_LABELS, start=1):
        artifacts = _DRAFT_STEP_ARTIFACTS[label]
        is_complete = bool(artifacts) and all(key in completed_ids for key in artifacts)
        is_current = label == selected_step
        state = "current" if is_current else "complete" if is_complete else "pending"
        state_label = "Current" if is_current else "Done" if is_complete else "Pending"
        tiles.append(
            f'<div class="edd-draft-step edd-draft-step-{state}">'
            f'<div class="edd-draft-step-index">{index}</div>'
            '<div class="edd-draft-step-body">'
            f'<div class="edd-draft-step-title">{html.escape(label)}</div>'
            f'<div class="edd-draft-step-state">{state_label}</div>'
            "</div>"
            "</div>"
        )

    st.markdown(
        f'<div class="edd-draft-stepper">{"".join(tiles)}</div>',
        unsafe_allow_html=True,
    )


def _render_target_step(agent_key: str, agent_target: dict[str, object]) -> None:
    _render_target_editor(agent_key, agent_target)
    _render_artifact_cards(draft_artifact_cards(agent_key))


def _render_design_step(
    agent_key: str,
    artifacts: dict[str, dict[str, object]],
    target_path: Path,
) -> None:
    import streamlit as st
    import yaml

    st.markdown("## Design Artifacts")
    ready_count = len(artifacts) - (0 if "target" not in artifacts else 1)
    col_scaffold, col_status = st.columns([1, 2])
    if col_scaffold.button("Scaffold design artifacts", type="primary"):
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
            save_draft_scenario(agent_key=agent_key, problem=clean_problem)
            run_draft_v0(agent_key)
            st.rerun()

    run = load_draft_artifacts(agent_key).get("v0_run", {}).get("run")
    if run:
        st.caption(str(target_path.parent / DRAFT_ARTIFACT_FILES["v0_run"]))
        st.markdown(run["final_response"])
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
        st.dataframe(eval_summary["checks"], use_container_width=True, hide_index=True)
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
        st.dataframe(v1_eval["checks"], use_container_width=True, hide_index=True)
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


def _render_artifact_cards(cards: list[dict[str, str]]) -> None:
    import streamlit as st

    st.markdown("## Artifact Review")
    for start in range(0, len(cards), 3):
        columns = st.columns(3)
        for column, card in zip(columns, cards[start : start + 3], strict=False):
            status = card["status"]
            pill = status_pill(status.upper(), "green" if status == "ready" else "blue")
            with column:
                st.markdown(
                    f"""
                    <div class="edd-card-soft">
                      <div class="edd-card-title">{html.escape(card["artifact"])}</div>
                      <div class="edd-card-subtitle">
                        {html.escape(card["group"])} · {pill}<br/>
                        {html.escape(card["action"])} ·
                        <code>{html.escape(card["file"])}</code>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_draft_progress(status: dict[str, object]) -> None:
    import streamlit as st

    completed = int(status["completed"])
    total = int(status["total"])
    st.progress(float(status["percent"]), text=f"{completed} of {total} steps complete")
    with st.expander("Step status", expanded=False):
        rows = [
            {
                "step": row["step"],
                "status": "complete" if row["complete"] else "pending",
            }
            for row in status["steps"]
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


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
