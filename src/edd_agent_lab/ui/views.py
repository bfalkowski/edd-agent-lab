"""Render helpers for the reference-scenario lab workbench."""

from __future__ import annotations

import html
from typing import Any

from edd_agent_lab.evals.scorecard import SuiteRunSnapshot
from edd_agent_lab.ui.layout import page_header, status_pill


def metric_card(label: str, value: str, help_text: str | None = None) -> None:
    import streamlit as st

    help_html = (
        f'<div class="edd-metric-help">{html.escape(help_text)}</div>' if help_text else ""
    )
    st.markdown(
        f"""
        <div class="edd-metric">
          <div class="edd-metric-label">{html.escape(label)}</div>
          <div class="edd-metric-value">{html.escape(value)}</div>
          {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_lifecycle_strip() -> None:
    import streamlit as st

    st.markdown(
        """
        <div class="edd-loop edd-loop-4">
          <div class="edd-loop-step">
            <div class="edd-loop-number">1</div>
            <div class="edd-loop-title">Design</div>
            <div class="edd-loop-text">Target, rules, eval contract, and tool requirements.</div>
          </div>
          <div class="edd-loop-step">
            <div class="edd-loop-number">2</div>
            <div class="edd-loop-title">Build</div>
            <div class="edd-loop-text">Graph versions and mock tool bindings.</div>
          </div>
          <div class="edd-loop-step">
            <div class="edd-loop-number">3</div>
            <div class="edd-loop-title">Evaluate</div>
            <div class="edd-loop-text">Run scenarios, capture failures, compare versions.</div>
          </div>
          <div class="edd-loop-step">
            <div class="edd-loop-number">4</div>
            <div class="edd-loop-title">Promote</div>
            <div class="edd-loop-text">Gate on behavior, tool readiness, and production.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def reference_context_rows(artifacts: dict[str, Any]) -> list[tuple[str, str]]:
    gate = artifacts["gate_result"]
    return [
        ("Reference scenario", artifacts["agent"]["name"]),
        ("Target", artifacts["target"]["id"]),
        ("Eval contract", artifacts["eval_contract"]["id"]),
        ("Demo gate", str(gate["overall_status"]).replace("_", " ")),
    ]


def lifecycle_story_lines(artifacts: dict[str, Any]) -> list[str]:
    failure = artifacts["failure_packet"]
    gate = artifacts["gate_result"]
    return [
        "Design target, behavior rules, eval contract, and tool requirements on the platform.",
        "Build v0-baseline and v1-evidence-triage-graph mock graphs in the lab.",
        (
            f"Evaluate — v0 fails `{failure['id']}` on `{failure['failed_rule']}`; "
            f"v1 resolves it with structured evidence."
        ),
        f"Promote when gates pass — reference outcome: {gate['overall_status'].replace('_', ' ')}.",
    ]


def render_context_metrics(artifacts: dict[str, Any]) -> None:
    import streamlit as st

    rows = reference_context_rows(artifacts)
    columns = st.columns(len(rows))
    for column, (label, value) in zip(columns, rows, strict=True):
        with column:
            metric_card(label, value)


def render_scenario_card(*, title: str, problem: str) -> None:
    import streamlit as st

    st.markdown(
        f"""
        <div class="edd-card">
          <div class="edd-card-title">{html.escape(title)}</div>
          <div class="edd-card-subtitle">{html.escape(problem.strip())}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_version_panel(
    *,
    version: str,
    response: str | None,
    snapshot: SuiteRunSnapshot | None,
) -> None:
    import streamlit as st

    header = html.escape(version)
    if snapshot is not None:
        pill = "green" if snapshot.passed else "red"
        header += f" {status_pill(f'{snapshot.overall_score:.2f}', pill)}"
    st.markdown(f'<div class="edd-version-title">{header}</div>', unsafe_allow_html=True)

    if response is None:
        st.info("No triage output yet — use **Run mock triage** above to compare responses.")
        return

    with st.container(border=True):
        st.markdown(response)

    if snapshot is None:
        return

    st.caption(f"Run `{snapshot.run_id}` · suite `{snapshot.suite_id}`")
    if snapshot.failure_packet_path:
        st.caption(f"Failure packet: `{snapshot.failure_packet_path}`")

    check_rows = []
    for case in snapshot.summary.get("cases") or []:
        for check in case.get("checks") or []:
            check_rows.append(
                {
                    "check": check.get("id"),
                    "score": check.get("score"),
                    "passed": check.get("passed"),
                    "comment": (check.get("comment") or "")[:120],
                }
            )
    if check_rows:
        st.dataframe(check_rows, use_container_width=True, hide_index=True)


def render_failure_story(artifacts: dict[str, Any]) -> None:
    import streamlit as st

    packet = artifacts["failure_packet"]
    with st.expander("v0 failure packet (reference)", expanded=True):
        page_header(packet["id"], f"Failed rule: {packet['failed_rule']}")
        st.markdown(f"**Observed:** {packet.get('observed_behavior', '').strip()}")
        st.markdown(f"**Expected:** {packet.get('expected_behavior', '').strip()}")
        st.markdown(f"**Recommended fix:** {packet.get('recommended_fix', '').strip()}")


def render_promotion_story(artifacts: dict[str, Any]) -> None:
    import streamlit as st

    fix_plan = artifacts["fix_plan"]
    comparison = artifacts["comparison"]
    gate = artifacts["gate_result"]
    with st.expander("v1 fix plan, comparison, and gate", expanded=False):
        page_header(fix_plan["id"], "Reference promotion bundle for publish v2")
        st.markdown("**Rules addressed:** " + ", ".join(
            fix_plan.get("behavior_rule_ids_addressed")
            or fix_plan.get("failed_rules_addressed")
            or []
        ))
        st.markdown("**Graph changes:**")
        for item in fix_plan.get("graph_changes") or []:
            st.markdown(f"- {item}")
        resolved = (
            comparison.get("resolved_failure_packet_ids")
            or comparison.get("resolved_failures")
            or []
        )
        st.markdown(
            f"**Comparison:** {comparison['baseline_version_id']} → "
            f"{comparison['candidate_version_id']} · resolved {', '.join(resolved)}"
        )
        st.markdown(
            f"**Gate:** {status_pill(gate['overall_status'].replace('_', ' '), 'green')}",
            unsafe_allow_html=True,
        )
        for blocker in gate.get("blockers") or []:
            st.caption(f"Blocker: {blocker}")


def render_mock_evidence_panel(bundle: dict[str, Any]) -> None:
    import streamlit as st

    customer = bundle.get("customer_report") or {}
    trace = bundle.get("langfuse_trace_summary") or {}
    evals = bundle.get("eval_results") or {}
    changes = bundle.get("recent_changes") or {}
    tools = bundle.get("tool_health") or {}

    with st.expander("Mock evidence bundle (Apex Health)", expanded=False):
        tab_customer, tab_trace, tab_evals, tab_changes, tab_tools = st.tabs(
            ["Customer", "Trace", "Evals", "Changes", "Tools"]
        )
        with tab_customer:
            st.json(customer)
        with tab_trace:
            st.markdown(f"**Latency trend:** {trace.get('latency_trend', 'unknown')}")
            st.markdown("**Notable patterns**")
            for item in trace.get("notable_patterns") or []:
                st.markdown(f"- {item}")
            st.markdown("**Errors**")
            for item in trace.get("error_patterns") or []:
                st.markdown(f"- {item}")
        with tab_evals:
            st.markdown(f"**Trend:** {evals.get('overall_score_trend', 'unknown')}")
            st.markdown(f"**Affected cases:** {evals.get('affected_case_type', 'unknown')}")
            st.caption(str(evals.get("score_drop_summary", "")).strip())
        with tab_changes:
            for change in changes.get("changes") or []:
                st.markdown(
                    f"- **{change.get('name')}** ({change.get('type')}) — "
                    f"{change.get('summary')} · {change.get('deployed_at')}"
                )
        with tab_tools:
            for tool in tools.get("tools") or []:
                st.markdown(
                    f"- **{tool.get('name')}** · {tool.get('status')} — "
                    f"{tool.get('issue')} ({tool.get('observed_frequency')})"
                )


def render_comparison_metrics(artifacts: dict[str, Any]) -> None:
    import streamlit as st

    from edd_agent_lab.ui.reference_data import comparison_metric_rows

    rows = comparison_metric_rows(artifacts)
    if not rows:
        return
    st.markdown("## Metric comparison (reference)")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    summary = (artifacts.get("comparison") or {}).get("summary")
    if summary:
        st.caption(str(summary).strip())


def render_trace_links(artifacts: dict[str, Any]) -> None:
    import streamlit as st

    from edd_agent_lab.ui.reference_data import trace_link_rows

    rows = trace_link_rows(artifacts)
    if not rows:
        return
    with st.expander("Trace links (reference)", expanded=False):
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_workbench_workflow(*, demo_ran: bool, failure_rule: str) -> None:
    import streamlit as st

    st.markdown("## Workbench workflow")
    steps = [
        ("Review scenario", "Problem statement, mock evidence, and EDD lifecycle context."),
        (
            "Run mock triage",
            (
                f"Compare {failure_rule or 'behavior'} across "
                "v0-baseline and v1-evidence-triage-graph."
            ),
        ),
        ("Evaluate", "Run the escalation_triage suite and inspect scores / failure packets."),
        ("Publish", "Push run-records to the platform when the API and EvalSpec are configured."),
    ]
    for index, (title, detail) in enumerate(steps, start=1):
        status = "done" if (index == 1 or (demo_ran and index <= 2)) else "todo"
        step_label = "done" if status == "done" else f"step {index}"
        step_pill = "green" if status == "done" else "blue"
        pill = status_pill(step_label, step_pill)
        st.markdown(
            f"{pill} **{html.escape(title)}** — {html.escape(detail)}",
            unsafe_allow_html=True,
        )
    if not demo_ran:
        st.caption(
            "Start with **Run mock triage** for a fast v0 vs v1 comparison, "
            "or **Run full demo** for triage + eval."
        )


def render_reference_publish_preview(artifacts: dict[str, Any]) -> None:
    import streamlit as st

    from edd_agent_lab.ui.reference_data import comparison_metric_rows, trace_link_rows

    packet = artifacts["failure_packet"]
    gate = artifacts["gate_result"]
    comparison = artifacts["comparison"]
    with st.expander("Preview: reference publish bundle (static)", expanded=False):
        st.caption(
            "Illustrates what a successful v1 publish looks like on the platform. "
            "Run the demo path to generate your own run-records below."
        )
        st.markdown(
            f"**Failure packet** `{packet['id']}` · failed rule `{packet['failed_rule']}`"
        )
        st.markdown(f"**Gate outcome** {gate['overall_status'].replace('_', ' ')}")
        resolved = (
            comparison.get("resolved_failure_packet_ids")
            or comparison.get("resolved_failures")
            or []
        )
        st.markdown(
            f"**Comparison** {comparison['baseline_version_id']} → "
            f"{comparison['candidate_version_id']} · resolves {', '.join(resolved)}"
        )
        metric_rows = comparison_metric_rows(artifacts)
        if metric_rows:
            st.dataframe(metric_rows, use_container_width=True, hide_index=True)
        trace_rows = trace_link_rows(artifacts)
        if trace_rows:
            st.dataframe(trace_rows, use_container_width=True, hide_index=True)


def render_version_highlights(
    *,
    v0_response: str | None,
    v1_response: str | None,
    failure_rule: str,
) -> None:
    import streamlit as st

    if not v0_response and not v1_response:
        return

    st.markdown("## Why v0 fails · why v1 passes")
    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown(
            f"{status_pill('v0 issue', 'red')} Claims a likely root cause without "
            f"`{failure_rule}` structure.",
            unsafe_allow_html=True,
        )
        if v0_response:
            st.caption("Look for unsupported root-cause language in the v0 response above.")
    with right:
        st.markdown(
            f"{status_pill('v1 fix', 'green')} Uses Facts / Hypotheses / Unknowns and a "
            "customer-safe update.",
            unsafe_allow_html=True,
        )
        if v1_response:
            st.caption("v1 keeps the root cause unconfirmed and lists investigation actions.")
