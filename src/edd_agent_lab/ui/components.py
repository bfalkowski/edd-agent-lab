"""Streamlit rendering helpers for the side-by-side console."""

from __future__ import annotations

import html
from typing import Any, Literal

from edd_agent_lab.evals.session_scoring import SessionScoreSummary
from edd_agent_lab.evals.turn_schemas import TurnComparison, TurnEvaluation, TurnVersionResult
from edd_agent_lab.ui.layout import page_header, status_pill

Side = Literal["left", "right"]


def build_side_history(
    turns: list[dict[str, str]],
    side: Side,
) -> list[dict[str, str]]:
    """Build per-version chat history from shared turn records."""
    response_key = "left_response" if side == "left" else "right_response"
    history: list[dict[str, str]] = []
    for turn in turns:
        history.append({"role": "user", "content": turn["user"]})
        history.append({"role": "assistant", "content": turn[response_key]})
    return history


def render_session_summary(summary: SessionScoreSummary) -> None:
    import streamlit as st

    with st.expander("Session score summary (all turns)", expanded=summary.turn_count >= 2):
        page_header("Session rollup", summary.session_decision)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(summary.left_version, f"{summary.left_avg_score:.3f}")
        c2.metric(summary.right_version, f"{summary.right_avg_score:.3f}")
        c3.metric("Avg delta", f"{summary.avg_delta:+.3f}")
        c4.metric("Turns", str(summary.turn_count))
        decision_status = "green" if summary.avg_delta > 0 else "blue"
        st.markdown(
            f"Decision: {status_pill(summary.session_decision, decision_status)}",
            unsafe_allow_html=True,
        )
        st.caption(summary.explanation)
        st.caption(
            f"Turn wins — {summary.left_version}: {summary.left_turns_won} · "
            f"{summary.right_version}: {summary.right_turns_won} · "
            f"Ties: {summary.tie_turns}"
        )
        with st.expander("Per-turn scores"):
            st.dataframe(
                [
                    {
                        "turn": item.turn_id,
                        "user_input": item.user_input[:80],
                        summary.left_version: item.left_score,
                        summary.right_version: item.right_score,
                        "delta": item.score_delta,
                        "decision": item.decision,
                    }
                    for item in summary.per_turn
                ],
                use_container_width=True,
                hide_index=True,
            )


def render_turn_analysis(comparison: TurnComparison, evaluation: TurnEvaluation) -> None:
    import streamlit as st

    with st.expander("Turn-level EDD analysis (latest message)", expanded=True):
        page_header("Latest turn comparison", comparison.decision)
        c1, c2, c3 = st.columns(3)
        c1.metric("Left score", f"{comparison.before_score:.3f}")
        c2.metric("Right score", f"{comparison.after_score:.3f}")
        c3.metric("Delta", f"{comparison.score_delta:+.3f}")
        decision_status = "green" if comparison.score_delta > 0 else "blue"
        st.markdown(
            f"Decision: {status_pill(comparison.decision, decision_status)}",
            unsafe_allow_html=True,
        )
        st.caption(comparison.explanation)
        st.caption(
            f"Improved: {', '.join(comparison.improved_checks) or '(none)'} · "
            f"Regressed: {', '.join(comparison.regressed_checks) or '(none)'}"
        )
        with st.expander("Evaluation JSON"):
            st.json(evaluation.model_dump())


def render_version_score(version: str, latest_result: TurnVersionResult | None) -> None:
    import streamlit as st

    if not latest_result:
        return
    pill = "green" if latest_result.passed else "yellow"
    st.markdown(
        f"{html.escape(version)} latest: "
        f"{status_pill(f'{latest_result.overall_score:.3f}', pill)}",
        unsafe_allow_html=True,
    )
    with st.popover("Check details"):
        for check in latest_result.checks:
            st.write(
                f"**{check.id}** — {check.score:.3f} "
                f"({'pass' if check.passed else 'fail'})"
            )


def render_side_by_side_chat(
    turns: list[dict[str, str]],
    left_version: str,
    right_version: str,
    left_result: TurnVersionResult | None = None,
    right_result: TurnVersionResult | None = None,
) -> None:
    """Render shared user turns with side-by-side assistant replies."""
    import streamlit as st

    header_left, header_right = st.columns(2, gap="medium")
    with header_left:
        st.markdown(
            f'<div class="edd-chat-column-title">{html.escape(left_version)}</div>',
            unsafe_allow_html=True,
        )
    with header_right:
        st.markdown(
            f'<div class="edd-chat-column-title">{html.escape(right_version)}</div>',
            unsafe_allow_html=True,
        )

    chat_box = st.container(height=460, border=True)
    with chat_box:
        if not turns:
            st.markdown(
                '<p class="edd-chat-empty">Send a message below — both agents receive '
                "the same prompt each turn.</p>",
                unsafe_allow_html=True,
            )
        for turn in turns:
            with st.chat_message("user"):
                st.markdown(turn["user"])
            left_col, right_col = st.columns(2, gap="small")
            with left_col:
                with st.chat_message("assistant"):
                    st.markdown(turn["left_response"])
            with right_col:
                with st.chat_message("assistant"):
                    st.markdown(turn["right_response"])

    score_left, score_right = st.columns(2, gap="medium")
    with score_left:
        render_version_score(left_version, left_result)
    with score_right:
        render_version_score(right_version, right_result)


def render_artifacts_panel(artifact_dir: str | None, evaluation: TurnEvaluation | None) -> None:
    import streamlit as st

    with st.expander("Evidence and artifacts"):
        if not artifact_dir:
            st.info("Send a message to generate turn artifacts.")
            return
        st.code(artifact_dir)
        if evaluation:
            st.json(evaluation.model_dump())


def init_session_defaults() -> None:
    import streamlit as st
    from datetime import UTC, datetime

    from edd_agent_lab.evals.turn_artifacts import new_session_id
    from edd_agent_lab.ui.session_store import (
        ConsoleSession,
        load_console_session,
        load_latest_turn_eval,
        save_console_session,
    )

    st.session_state.pop("left_messages", None)
    st.session_state.pop("right_messages", None)

    if st.session_state.get("_console_initialized"):
        return

    requested = st.query_params.get("session_id")
    if requested:
        loaded = load_console_session(requested)
        if loaded is not None:
            _apply_loaded_session(st, loaded)
            evaluation, comparison = load_latest_turn_eval(requested)
            st.session_state.latest_evaluation = evaluation
            st.session_state.latest_comparison = comparison
            st.session_state._console_initialized = True
            return

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    session_id = new_session_id()
    defaults: dict[str, Any] = {
        "session_id": session_id,
        "left_version": "v0-baseline",
        "right_version": "v1-discovery-graph",
        "scenario_id": "healthcare_documentation",
        "suite_id": "discovery_quality",
        "turns": [],
        "latest_evaluation": None,
        "latest_comparison": None,
        "latest_artifact_dir": None,
        "turn_count": 0,
    }
    for key, value in defaults.items():
        st.session_state[key] = value

    console_session = ConsoleSession(
        session_id=session_id,
        created_at=now,
        updated_at=now,
        scenario_id=defaults["scenario_id"],
        suite_id=defaults["suite_id"],
        left_version=defaults["left_version"],
        right_version=defaults["right_version"],
    )
    st.session_state.console_session = console_session
    save_console_session(console_session)
    st.query_params["session_id"] = session_id
    st.session_state._console_initialized = True


def start_new_console_session() -> None:
    import streamlit as st
    from datetime import UTC, datetime

    from edd_agent_lab.evals.turn_artifacts import new_session_id
    from edd_agent_lab.ui.session_store import ConsoleSession, save_console_session

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    session_id = new_session_id()
    st.session_state.session_id = session_id
    st.session_state.turns = []
    st.session_state.latest_evaluation = None
    st.session_state.latest_comparison = None
    st.session_state.latest_artifact_dir = None
    st.session_state.turn_count = 0
    console_session = ConsoleSession(
        session_id=session_id,
        created_at=now,
        updated_at=now,
        scenario_id=st.session_state.scenario_id,
        suite_id=st.session_state.suite_id,
        left_version=st.session_state.left_version,
        right_version=st.session_state.right_version,
    )
    st.session_state.console_session = console_session
    save_console_session(console_session)
    st.query_params["session_id"] = session_id


def sync_console_session() -> "ConsoleSession":
    import streamlit as st

    from edd_agent_lab.ui.session_store import ChatTurn, ConsoleSession, save_console_session

    session: ConsoleSession = st.session_state.console_session
    session.scenario_id = st.session_state.scenario_id
    session.suite_id = st.session_state.suite_id
    session.left_version = st.session_state.left_version
    session.right_version = st.session_state.right_version
    session.chat_turns = [ChatTurn.model_validate(turn) for turn in st.session_state.turns]
    session.latest_artifact_dir = st.session_state.get("latest_artifact_dir")
    st.session_state.console_session = session
    save_console_session(session)
    return session


def _apply_loaded_session(st: Any, session: "ConsoleSession") -> None:
    from edd_agent_lab.ui.session_store import ConsoleSession

    assert isinstance(session, ConsoleSession)
    st.session_state.session_id = session.session_id
    st.session_state.scenario_id = session.scenario_id
    st.session_state.suite_id = session.suite_id
    st.session_state.left_version = session.left_version
    st.session_state.right_version = session.right_version
    st.session_state.turns = [turn.model_dump() for turn in session.chat_turns]
    st.session_state.turn_count = len(session.chat_turns)
    st.session_state.latest_artifact_dir = session.latest_artifact_dir
    st.session_state.console_session = session
