"""Streamlit eval and publish controls for the reference workbench."""

from __future__ import annotations

import os
from typing import Any

from edd_agent_lab.ui.layout import page_header, status_pill
from edd_agent_lab.ui.reference_core import (
    V0,
    V1,
    eval_spec_configured,
    platform_api_base_url,
    platform_console_url,
    publish_version_run,
    run_suite_for_version,
    snapshot_from_dict,
    snapshot_to_dict,
)


def render_workbench_actions() -> None:
    import streamlit as st

    page_header(
        "Evaluate & publish",
        "Run the reference suite and push run-records to the platform",
    )
    st.caption("Agent `customer-escalation-triage` · suite `escalation_triage`")

    left, right, both = st.columns(3)
    if left.button(f"Run eval ({V0})", use_container_width=True):
        with st.spinner(f"Running escalation_triage on {V0}…"):
            st.session_state.v0_snapshot = snapshot_to_dict(run_suite_for_version(V0))
        st.rerun()
    if right.button(f"Run eval ({V1})", use_container_width=True):
        with st.spinner(f"Running escalation_triage on {V1}…"):
            st.session_state.v1_snapshot = snapshot_to_dict(run_suite_for_version(V1))
        st.rerun()
    if both.button("Run eval (both)", use_container_width=True):
        with st.spinner("Running escalation_triage on both versions…"):
            st.session_state.v0_snapshot = snapshot_to_dict(run_suite_for_version(V0))
            st.session_state.v1_snapshot = snapshot_to_dict(run_suite_for_version(V1))
        st.rerun()

    v0_snap = snapshot_from_dict(st.session_state.get("v0_snapshot"))
    v1_snap = snapshot_from_dict(st.session_state.get("v1_snapshot"))
    if v0_snap or v1_snap:
        c1, c2, c3 = st.columns(3)
        c1.metric(V0, f"{v0_snap.overall_score:.3f}" if v0_snap else "—")
        c2.metric(V1, f"{v1_snap.overall_score:.3f}" if v1_snap else "—")
        if v0_snap and v1_snap:
            c3.metric("Delta", f"{v1_snap.overall_score - v0_snap.overall_score:+.3f}")

    st.divider()
    st.markdown("**Publish to platform**")
    api_base = platform_api_base_url()
    if not api_base:
        st.info("Set `EDD_API_BASE_URL` and `EDD_CLIENT_MODE=http` in `.env` to publish.")
    elif not eval_spec_configured():
        st.warning("Set `EDD_EVAL_SPEC_ID` in `.env` before publishing.")
    else:
        st.caption(f"API: {api_base} · EvalSpec: {os.environ.get('EDD_EVAL_SPEC_ID', '')[:8]}…")

    pub_v0, pub_v1, pub_both = st.columns(3)
    if pub_v0.button(f"Publish {V0}", use_container_width=True):
        _handle_publish(V0)
    if pub_v1.button(f"Publish {V1}", use_container_width=True):
        _handle_publish(V1)
    if pub_both.button("Publish both", use_container_width=True):
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


def snapshot_from_state(st: Any, key: str):
    return snapshot_from_dict(st.session_state.get(key))


def _handle_publish_both() -> None:
    import streamlit as st

    publishes: list[dict[str, Any]] = []
    for agent_version in (V0, V1):
        try:
            with st.spinner(f"Publishing {agent_version}…"):
                result = publish_version_run(agent_version)
        except FileNotFoundError as exc:
            st.error(str(exc))
            st.caption(f"Run the eval suite for {agent_version} first.")
            return
        except Exception as exc:
            st.error(f"Publish failed for {agent_version}: {exc}")
            return
        publishes.append(
            {
                "agent_version": agent_version,
                "status": result.get("status"),
                "platform_run_id": result.get("platform_run_id"),
                "gate_status": result.get("gate_status"),
                "gate_explanation": result.get("gate_explanation"),
                "queue_path": result.get("queue_path"),
            }
        )
    st.session_state.last_publish = publishes[-1]
    st.session_state.last_publish_batch = publishes
    st.rerun()


def _handle_publish(agent_version: str) -> None:
    import streamlit as st

    try:
        with st.spinner(f"Publishing {agent_version}…"):
            result = publish_version_run(agent_version)
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


def _render_publish_status(publish: dict[str, Any]) -> None:
    import streamlit as st

    gate = publish.get("gate_status")
    gate_pill = {"pass": "green", "fail": "red", "insufficient_evidence": "blue"}.get(
        str(gate),
        "blue",
    )
    st.markdown(
        f"Last publish — `{publish.get('agent_version')}` · "
        f"status `{publish.get('status')}` · "
        f"gate {status_pill(str(gate), gate_pill)}",
        unsafe_allow_html=True,
    )
    run_id = publish.get("platform_run_id")
    if run_id:
        api_base = platform_api_base_url()
        st.code(str(run_id))
        if api_base:
            st.caption(f"{api_base.rstrip('/')}/v1/experiment-runs/{run_id}/evidence")
        st.markdown(
            f"[Platform console]({platform_console_url()}) · "
            f"[Failure packets]({platform_console_url('failure_packets')}) · "
            f"[Compare versions]({platform_console_url('compare_versions')})"
        )
    if publish.get("gate_explanation"):
        st.caption(str(publish["gate_explanation"]))
