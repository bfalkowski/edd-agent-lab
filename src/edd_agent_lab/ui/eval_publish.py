"""Console eval suite runner and platform publish panel."""

from __future__ import annotations

import os
from typing import Any

from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.evals.scorecard import SuiteRunSnapshot, snapshot_from_eval_result
from edd_agent_lab.integrations.edd_client import get_edd_client, publish_run_record_file
from edd_agent_lab.integrations.lab_runs import run_record_path


def run_suite_for_version(
    *,
    agent_key: str,
    suite_id: str,
    agent_version: str,
) -> SuiteRunSnapshot:
    result = run_eval_suite(
        agent_key=agent_key,
        suite_id=suite_id,
        agent_version=agent_version,
    )
    return snapshot_from_eval_result(result, suite_id)


def publish_version_run(
    *,
    agent_key: str,
    agent_version: str,
) -> dict[str, Any]:
    record_path = run_record_path(agent_key, agent_version)
    if not record_path.is_file():
        raise FileNotFoundError(f"Run record not found: {record_path}")
    return publish_run_record_file(record_path, client=get_edd_client())


def platform_api_base_url() -> str | None:
    base = os.environ.get("EDD_API_BASE_URL", "").strip()
    return base or None


def platform_console_url() -> str:
    return os.environ.get("EDD_CONSOLE_BASE_URL", "http://127.0.0.1:8501").strip()


def eval_spec_configured() -> bool:
    return bool(os.environ.get("EDD_EVAL_SPEC_ID", "").strip())


def render_eval_publish_panel(
    *,
    agent_key: str,
    suite_id: str,
    left_version: str,
    right_version: str,
) -> None:
    import streamlit as st

    from edd_agent_lab.ui.layout import page_header, status_pill

    st.markdown("---")
    with st.expander("Eval suite & platform publish", expanded=False):
        page_header("Validate & promote", "Run suite scorecard and publish to platform")
        st.caption(f"Suite: **{suite_id}** · Agent: customer-solution")

        suite_results: dict[str, dict[str, Any]] = st.session_state.setdefault("suite_results", {})
        left_key = f"{suite_id}:{left_version}"
        right_key = f"{suite_id}:{right_version}"

        btn_left, btn_right, btn_both = st.columns(3)
        if btn_left.button(f"Run suite ({left_version})", use_container_width=True):
            with st.spinner(f"Running {suite_id} on {left_version}…"):
                snapshot = run_suite_for_version(
                    agent_key=agent_key,
                    suite_id=suite_id,
                    agent_version=left_version,
                )
                suite_results[left_key] = _snapshot_to_dict(snapshot)
                st.session_state.suite_results = suite_results
                st.rerun()
        if btn_right.button(f"Run suite ({right_version})", use_container_width=True):
            with st.spinner(f"Running {suite_id} on {right_version}…"):
                snapshot = run_suite_for_version(
                    agent_key=agent_key,
                    suite_id=suite_id,
                    agent_version=right_version,
                )
                suite_results[right_key] = _snapshot_to_dict(snapshot)
                st.session_state.suite_results = suite_results
                st.rerun()
        if btn_both.button("Run both versions", use_container_width=True):
            with st.spinner(f"Running {suite_id} on both versions…"):
                for version, key in (
                    (left_version, left_key),
                    (right_version, right_key),
                ):
                    snapshot = run_suite_for_version(
                        agent_key=agent_key,
                        suite_id=suite_id,
                        agent_version=version,
                    )
                    suite_results[key] = _snapshot_to_dict(snapshot)
                st.session_state.suite_results = suite_results
                st.rerun()

        left_snap = _dict_to_snapshot(suite_results.get(left_key))
        right_snap = _dict_to_snapshot(suite_results.get(right_key))
        if left_snap or right_snap:
            _render_suite_comparison(
                st,
                status_pill,
                left_snap,
                right_snap,
                left_version,
                right_version,
            )

        st.divider()
        st.markdown("**Publish to platform**")
        api_base = platform_api_base_url()
        if not api_base:
            st.info(
                "Set `EDD_API_BASE_URL` (e.g. http://127.0.0.1:8000) and "
                "`EDD_CLIENT_MODE=http` in `.env` to publish."
            )
        elif not eval_spec_configured():
            st.warning(
                "Set `EDD_EVAL_SPEC_ID` in `.env` to the platform EvalSpec UUID "
                "before publishing."
            )
        else:
            st.caption(f"API: {api_base} · EvalSpec: {os.environ.get('EDD_EVAL_SPEC_ID', '')[:8]}…")

        pub_left, pub_right = st.columns(2)
        if pub_left.button(f"Publish {left_version}", use_container_width=True):
            _handle_publish(st, agent_key=agent_key, agent_version=left_version)
        if pub_right.button(f"Publish {right_version}", use_container_width=True):
            _handle_publish(st, agent_key=agent_key, agent_version=right_version)

        last_publish = st.session_state.get("last_publish")
        if last_publish:
            _render_publish_status(st, status_pill, last_publish)


def _handle_publish(st: Any, *, agent_key: str, agent_version: str) -> None:
    try:
        with st.spinner(f"Publishing {agent_version}…"):
            result = publish_version_run(agent_key=agent_key, agent_version=agent_version)
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.caption("Run the eval suite for this version first.")
        return
    except Exception as exc:
        st.error(f"Publish failed: {exc}")
        return

    st.session_state.last_publish = {
        "agent_version": agent_version,
        "status": result.get("status"),
        "platform_run_id": result.get("platform_run_id"),
        "gate_status": result.get("gate_status"),
        "gate_explanation": result.get("gate_explanation"),
        "queue_path": result.get("queue_path"),
    }
    st.rerun()


def _render_suite_comparison(
    st: Any,
    status_pill: Any,
    left: SuiteRunSnapshot | None,
    right: SuiteRunSnapshot | None,
    left_version: str,
    right_version: str,
) -> None:
    st.markdown("**Suite scorecard**")
    overview_left, overview_right, overview_delta = st.columns(3)
    if left:
        overview_left.metric(left_version, f"{left.overall_score:.3f}")
    else:
        overview_left.metric(left_version, "—")
    if right:
        overview_right.metric(right_version, f"{right.overall_score:.3f}")
    else:
        overview_right.metric(right_version, "—")
    if left and right:
        overview_delta.metric("Delta", f"{right.overall_score - left.overall_score:+.3f}")

    for label, snap in ((left_version, left), (right_version, right)):
        if not snap:
            continue
        pill = "green" if snap.passed else "yellow"
        st.markdown(
            f"{label}: {status_pill(f'{snap.overall_score:.3f}', pill)} · run `{snap.run_id}`",
            unsafe_allow_html=True,
        )
        st.dataframe(
            [
                {
                    "item": row.item_id,
                    "scenario": row.scenario,
                    "score": row.score,
                    "passed": row.passed,
                    "detail": row.detail,
                }
                for row in snap.rows
            ],
            use_container_width=True,
            hide_index=True,
        )
        if snap.failure_packet_path:
            st.caption(f"Failure packet: `{snap.failure_packet_path}`")


def _render_publish_status(st: Any, status_pill: Any, publish: dict[str, Any]) -> None:
    st.markdown("**Last publish**")
    status = str(publish.get("status", "unknown"))
    gate = publish.get("gate_status")
    gate_pill = {"pass": "green", "fail": "yellow", "insufficient_evidence": "blue"}.get(
        str(gate),
        "blue",
    )
    c1, c2, c3 = st.columns(3)
    c1.write(f"Version: `{publish.get('agent_version')}`")
    c2.write(f"Status: `{status}`")
    if gate:
        c3.markdown(
            f"Gate: {status_pill(str(gate), gate_pill)}",
            unsafe_allow_html=True,
        )
    run_id = publish.get("platform_run_id")
    if run_id:
        api_base = platform_api_base_url()
        st.code(str(run_id))
        if api_base:
            st.caption(f"API run: {api_base.rstrip('/')}/v1/experiment-runs/{run_id}")
        st.markdown(
            f"[Open platform console]({platform_console_url()}) · Results Explorer",
        )
    if publish.get("gate_explanation"):
        st.caption(str(publish["gate_explanation"]))
    if publish.get("queue_path"):
        st.warning(f"Queued locally: {publish['queue_path']}")


def _snapshot_to_dict(snapshot: SuiteRunSnapshot) -> dict[str, Any]:
    return {
        "agent_version": snapshot.agent_version,
        "suite_id": snapshot.suite_id,
        "run_id": snapshot.run_id,
        "overall_score": snapshot.overall_score,
        "passed": snapshot.passed,
        "summary_path": snapshot.summary_path,
        "failure_packet_path": snapshot.failure_packet_path,
        "rows": [row.__dict__ for row in snapshot.rows],
        "summary": snapshot.summary,
    }


def _dict_to_snapshot(data: dict[str, Any] | None) -> SuiteRunSnapshot | None:
    if not data:
        return None
    from edd_agent_lab.evals.scorecard import SuiteScorecardRow

    rows = [SuiteScorecardRow(**row) for row in data.get("rows", [])]
    return SuiteRunSnapshot(
        agent_version=str(data["agent_version"]),
        suite_id=str(data["suite_id"]),
        run_id=str(data["run_id"]),
        overall_score=float(data["overall_score"]),
        passed=bool(data["passed"]),
        summary_path=str(data["summary_path"]),
        failure_packet_path=data.get("failure_packet_path"),
        rows=rows,
        summary=data.get("summary", {}),
    )
