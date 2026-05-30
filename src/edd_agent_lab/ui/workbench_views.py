"""Doc-12 lab workbench layout (context bar, comparison, verdict, details tabs)."""

from __future__ import annotations

import html
import os
from collections.abc import Callable
from typing import Any

from edd_agent_lab.evals.scorecard import SuiteRunSnapshot
from edd_agent_lab.ui.layout import page_header, status_pill
from edd_agent_lab.ui.reference_core import (
    SCENARIO_ID,
    V0,
    V1,
    eval_spec_configured,
    platform_api_base_url,
    platform_console_url,
    run_suite_for_version,
    snapshot_to_dict,
)
from edd_agent_lab.ui.reference_data import (
    comparison_metric_rows,
    graph_diff_rows,
    graph_flow_summary,
    list_reference_artifact_paths,
    load_graph_design_bundle,
    load_tool_binding_rows,
    reference_overall_score,
    trace_link_rows,
)
from edd_agent_lab.ui.workbench import _handle_publish, _handle_publish_both, _render_publish_status


def render_context_bar(
    *,
    artifacts: dict[str, Any],
    scenario_title: str,
    platform_health: dict[str, Any],
    on_run_v0: Callable[[], None],
    on_run_v1: Callable[[], None],
    on_compare: Callable[[], None],
    on_refresh: Callable[[], None],
) -> None:
    import streamlit as st

    agent_name = str(artifacts["agent"].get("name", "Customer Escalation Triage"))
    gate = artifacts["gate_result"]
    tool_mode = str(gate.get("tool_readiness_status", "mock_local")).replace("_", " ")
    platform_pill = "green" if platform_health.get("reachable") else (
        "yellow" if platform_health.get("configured") else "blue"
    )
    platform_label = (
        "connected"
        if platform_health.get("reachable")
        else "unreachable"
        if platform_health.get("configured")
        else "not configured"
    )

    st.markdown(
        f"""
        <div class="edd-card">
          <div class="edd-card-title">Context</div>
          <div class="edd-card-subtitle">
            Agent: {html.escape(agent_name)} ·
            Scenario: {html.escape(scenario_title)} ·
            Compare: {html.escape(V0)} vs {html.escape(V1)} ·
            Tool mode: {html.escape(tool_mode)} ·
            Model: fixture ·
            Platform: {status_pill(platform_label, platform_pill)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    run_v0, run_v1, compare, refresh = st.columns(4)
    if run_v0.button("Run v0", use_container_width=True, key="ctx_run_v0"):
        on_run_v0()
    if run_v1.button("Run v1", use_container_width=True, key="ctx_run_v1"):
        on_run_v1()
    if compare.button("Compare", type="primary", use_container_width=True, key="ctx_compare"):
        on_compare()
    if refresh.button("Refresh artifacts", use_container_width=True, key="ctx_refresh"):
        on_refresh()


def render_scenario_summary(*, title: str, problem: str, expected_themes: list[str]) -> None:
    import streamlit as st

    themes = "".join(f"<li>{html.escape(theme)}</li>" for theme in expected_themes)
    st.markdown(
        f"""
        <div class="edd-card">
          <div class="edd-card-title">{html.escape(title)}</div>
          <div class="edd-card-subtitle">{html.escape(problem.strip())}</div>
          <div class="edd-card-subtitle"><strong>Expected behavior</strong><ul>{themes}</ul></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _display_score(
    snapshot: SuiteRunSnapshot | None,
    *,
    artifacts: dict[str, Any],
    version: str,
) -> str:
    if snapshot is not None:
        return f"{snapshot.overall_score:.1f} / 5"
    ref = reference_overall_score(artifacts, "v0" if version == V0 else "v1")
    if ref is not None:
        return f"{ref:.1f} / 5 (reference)"
    return "—"


def _gate_label(
    *,
    version: str,
    snapshot: SuiteRunSnapshot | None,
    artifacts: dict[str, Any],
) -> tuple[str, str]:
    if version == V0:
        if snapshot is not None:
            passed = snapshot.passed
            label = "PASS" if passed else "FAIL"
            pill = "green" if passed else "red"
            return (label, pill)
        return ("FAIL", "red")
    gate = artifacts["gate_result"]
    overall_status = str(gate.get("overall_status", "pass_for_demo_not_production"))
    overall = overall_status.replace("_", " ").upper()
    pill = "green" if "pass" in overall_status.lower() else "red"
    return (overall, pill)


def render_version_panel_doc12(
    *,
    version: str,
    response: str | None,
    snapshot: SuiteRunSnapshot | None,
    artifacts: dict[str, Any],
    graph_summary: str,
    tool_mode: str,
    callout: str,
    callout_pill: str,
    production_status: str | None = None,
) -> None:
    import streamlit as st

    gate_label, gate_pill = _gate_label(version=version, snapshot=snapshot, artifacts=artifacts)
    score = _display_score(snapshot, artifacts=artifacts, version=version)
    title = html.escape(version)
    meta_parts = [
        f"Score: {html.escape(score)}",
        status_pill(gate_label, gate_pill),
        f"Graph: {html.escape(graph_summary)}",
        f"Tool mode: {html.escape(tool_mode)}",
    ]
    if production_status:
        meta_parts.append(status_pill(production_status, "yellow"))

    st.markdown(
        f"""
        <div class="edd-version-title">{title}</div>
        <div class="edd-card-subtitle">{" · ".join(meta_parts)}</div>
        """,
        unsafe_allow_html=True,
    )

    if response is None:
        st.info("No output yet — use **Run v0**, **Run v1**, or **Compare** in the context bar.")
        return

    with st.container(border=True):
        st.markdown(response)

    if snapshot is not None:
        st.caption(f"Run `{snapshot.run_id}` · suite `{snapshot.suite_id}`")

    st.markdown(
        f"{status_pill('Failure' if version == V0 else 'Improvement', callout_pill)} "
        f"{html.escape(callout)}",
        unsafe_allow_html=True,
    )


def render_edd_verdict(*, artifacts: dict[str, Any]) -> None:
    import streamlit as st

    failure = artifacts["failure_packet"]
    fix_plan = artifacts["fix_plan"]
    comparison = artifacts["comparison"]
    gate = artifacts["gate_result"]
    resolved = (
        comparison.get("resolved_failure_packet_ids")
        or comparison.get("resolved_failures")
        or []
    )
    graph_changes = fix_plan.get("graph_changes") or []
    blockers = gate.get("blockers") or []

    graph_change_text = ", ".join(f"`{item}`" for item in graph_changes[:5])
    if len(graph_changes) > 5:
        graph_change_text += "…"
    behavior_pill = status_pill(str(gate.get("behavior_gate_status", "pass")).upper(), "green")
    tool_status = str(gate.get("tool_readiness_status", "mock_local")).replace("_", " ").upper()
    tool_pill = status_pill(tool_status, "yellow")
    production_pill = status_pill(
        str(gate.get("production_readiness_status", "blocked")).upper(),
        "yellow",
    )
    promotion_pill = status_pill("PROMOTED FOR DEMO", "green")

    st.markdown("## EDD Verdict")
    st.markdown(
        f"""
        **v0 failed** because it overclaimed root cause.
        Failed rule: `{failure['failed_rule']}`.

        **v1 fixed the failure** by adding structured evidence collection and review:
        {graph_change_text}.

        **Resolved:** {", ".join(resolved) or "unsupported root-cause claim"}.

        **No new critical failures.**

        **Readiness**
        - Behavior readiness: {behavior_pill}
        - Tool readiness: {tool_pill}
        - Production readiness: {production_pill}
        - Promotion: {promotion_pill}
        """,
        unsafe_allow_html=True,
    )
    if blockers:
        st.markdown("**Remaining blockers**")
        for blocker in blockers:
            st.markdown(f"- {blocker}")
    summary = (comparison.get("summary") or "").strip()
    if summary:
        st.caption(summary)


def render_details_tabs(
    *,
    artifacts: dict[str, Any],
    platform_health: dict[str, Any],
) -> None:
    import streamlit as st

    v0_design, v0_nodes = load_graph_design_bundle("v0")
    v1_design, v1_nodes = load_graph_design_bundle("v1")
    diff_rows = graph_diff_rows(v0_nodes, v1_nodes)
    tool_rows = load_tool_binding_rows()
    score_rows = comparison_metric_rows(artifacts)
    trace_rows = trace_link_rows(artifacts)
    artifact_rows = list_reference_artifact_paths()

    st.markdown("## Details")
    tab_graph, tab_tools, tab_scores, tab_traces, tab_artifacts, tab_publish = st.tabs(
        ["Graph Diff", "Tools", "Scores", "Traces", "Artifacts", "Publish"]
    )

    with tab_graph:
        st.markdown(f"**v0 graph:** `{graph_flow_summary(v0_design, v0_nodes)}`")
        st.markdown(f"**v1 graph:** `{graph_flow_summary(v1_design, v1_nodes)}`")
        if diff_rows:
            st.dataframe(diff_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No added nodes detected between v0 and v1 bundles.")

    with tab_tools:
        if tool_rows:
            st.dataframe(tool_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Tool bindings not found — set `EDD_PLATFORM_ROOT` to the platform repo.")
        st.warning(
            "Production readiness is blocked because required tools are mock/local. "
            "This run is suitable for demo and offline evaluation only."
        )

    with tab_scores:
        if score_rows:
            st.dataframe(
                [
                    {
                        "metric": row["metric"],
                        "v0": row["v0"],
                        "v1": row["v1"],
                        "delta": row["delta"],
                        "rules": row["rules"],
                    }
                    for row in score_rows
                ],
                use_container_width=True,
                hide_index=True,
            )
        summary = (artifacts.get("comparison") or {}).get("summary")
        if summary:
            st.caption(str(summary).strip())

    with tab_traces:
        if trace_rows:
            st.dataframe(trace_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("No trace links in reference artifacts.")

    with tab_artifacts:
        if artifact_rows:
            st.dataframe(artifact_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Paths are read-only in the MVP — edit artifacts in the repo or platform console."
        )

    with tab_publish:
        _render_publish_tab(platform_health=platform_health)


def _render_publish_tab(*, platform_health: dict[str, Any]) -> None:
    import streamlit as st

    page_header("Publish to platform", "Push local run-records to the platform API")
    api_base = platform_api_base_url()
    if api_base:
        st.caption(f"Platform API: {api_base}")
    elif platform_health.get("configured"):
        st.warning(str(platform_health.get("message", "Platform API unreachable")))
    else:
        st.info("Set `EDD_API_BASE_URL` and `EDD_CLIENT_MODE=http` in `.env` to publish.")

    if api_base and eval_spec_configured():
        st.caption(f"EvalSpec: {os.environ.get('EDD_EVAL_SPEC_ID', '')[:8]}…")

    pub_v0, pub_v1, pub_both = st.columns(3)
    if pub_v0.button(f"Publish {V0}", use_container_width=True, key="pub_v0"):
        _handle_publish(V0)
    if pub_v1.button(f"Publish {V1}", use_container_width=True, key="pub_v1"):
        _handle_publish(V1)
    if pub_both.button("Publish both", use_container_width=True, key="pub_both"):
        _handle_publish_both()

    last_publish = st.session_state.get("last_publish")
    if last_publish:
        _render_publish_status(last_publish)

    batch = st.session_state.get("last_publish_batch") or []
    if len(batch) > 1:
        st.markdown("**Publish batch**")
        st.dataframe(
            [
                {
                    "version": item.get("agent_version"),
                    "gate": item.get("gate_status"),
                    "platform_run_id": item.get("platform_run_id"),
                    "error": item.get("error"),
                }
                for item in batch
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown(
        f"[Open platform console]({platform_console_url('overview')}) · "
        f"[Failure packets]({platform_console_url('failure_packets')}) · "
        f"[Compare versions]({platform_console_url('compare_versions')})"
    )


def run_v0_workflow(st: Any) -> None:
    from edd_agent_lab.agents.customer_escalation_triage.runner import (
        run_customer_escalation_triage,
    )

    with st.spinner(f"Running {V0} triage and eval…"):
        result = run_customer_escalation_triage(scenario_id=SCENARIO_ID, agent_version=V0)
        st.session_state.v0_response = result.final_response
        st.session_state.v0_snapshot = snapshot_to_dict(run_suite_for_version(V0))
    st.rerun()


def run_v1_workflow(st: Any) -> None:
    from edd_agent_lab.agents.customer_escalation_triage.runner import (
        run_customer_escalation_triage,
    )

    with st.spinner(f"Running {V1} triage and eval…"):
        result = run_customer_escalation_triage(scenario_id=SCENARIO_ID, agent_version=V1)
        st.session_state.v1_response = result.final_response
        st.session_state.v1_snapshot = snapshot_to_dict(run_suite_for_version(V1))
    st.rerun()


def run_compare_workflow(st: Any) -> None:
    from edd_agent_lab.agents.customer_escalation_triage.runner import (
        run_customer_escalation_triage,
    )

    with st.spinner("Running v0 and v1 triage + eval…"):
        v0 = run_customer_escalation_triage(scenario_id=SCENARIO_ID, agent_version=V0)
        v1 = run_customer_escalation_triage(scenario_id=SCENARIO_ID, agent_version=V1)
        st.session_state.v0_response = v0.final_response
        st.session_state.v1_response = v1.final_response
        st.session_state.v0_snapshot = snapshot_to_dict(run_suite_for_version(V0))
        st.session_state.v1_snapshot = snapshot_to_dict(run_suite_for_version(V1))
    st.rerun()
