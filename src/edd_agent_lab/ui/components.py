"""Streamlit rendering helpers for the side-by-side console."""

from __future__ import annotations

from typing import Any

from edd_agent_lab.evals.turn_schemas import TurnComparison, TurnEvaluation, TurnVersionResult


def render_turn_analysis(comparison: TurnComparison, evaluation: TurnEvaluation) -> None:
    import streamlit as st

    st.subheader("Turn-Level EDD Analysis")
    st.metric("Left score", f"{comparison.before_score:.3f}")
    st.metric("Right score", f"{comparison.after_score:.3f}")
    st.metric("Delta", f"{comparison.score_delta:+.3f}")
    st.write(f"**Decision:** {comparison.decision}")
    st.caption(comparison.explanation)
    st.write("Improved checks:", ", ".join(comparison.improved_checks) or "(none)")
    st.write("Regressed checks:", ", ".join(comparison.regressed_checks) or "(none)")
    st.write("Unchanged checks:", ", ".join(comparison.unchanged_checks) or "(none)")
    with st.expander("Evaluation JSON"):
        st.json(evaluation.model_dump())


def render_chat_panel(
    version: str,
    messages: list[dict[str, str]],
    latest_result: TurnVersionResult | None = None,
) -> None:
    import streamlit as st

    st.markdown(f"### {version}")
    for message in messages:
        role = message.get("role", "assistant")
        with st.chat_message(role):
            st.markdown(message.get("content", ""))
    if latest_result:
        st.caption(f"Turn score: {latest_result.overall_score:.3f}")
        if latest_result.passed:
            st.success("Pass")
        else:
            st.warning("Needs improvement")
        with st.expander("Check details"):
            for check in latest_result.checks:
                st.write(f"- {check.id}: {check.score:.3f} ({'pass' if check.passed else 'fail'})")


def render_artifacts_panel(artifact_dir: str | None, evaluation: TurnEvaluation | None) -> None:
    import streamlit as st

    st.subheader("Artifacts")
    if not artifact_dir:
        st.info("Run a turn to generate artifacts.")
        return
    st.code(artifact_dir)
    if evaluation:
        with st.expander("turn-evaluation.json"):
            st.json(evaluation.model_dump())


def init_session_defaults() -> None:
    import streamlit as st

    from edd_agent_lab.evals.turn_artifacts import new_session_id

    defaults: dict[str, Any] = {
        "session_id": new_session_id(),
        "left_version": "v0-baseline",
        "right_version": "v1-discovery-graph",
        "left_messages": [],
        "right_messages": [],
        "latest_evaluation": None,
        "latest_comparison": None,
        "latest_artifact_dir": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
