"""Streamlit side-by-side agent comparison console."""

from __future__ import annotations

from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_turn
from edd_agent_lab.agents.generation import resolve_generation_mode
from edd_agent_lab.evals.loading import list_eval_suite_ids
from edd_agent_lab.evals.turn_artifacts import new_turn_id, write_turn_artifacts
from edd_agent_lab.evals.turn_comparison import compare_turn_evaluation
from edd_agent_lab.evals.turn_evaluator import evaluate_turn
from edd_agent_lab.scenarios.loading import list_scenario_ids, load_scenario
from edd_agent_lab.ui.components import (
    build_side_history,
    init_session_defaults,
    render_artifacts_panel,
    render_side_by_side_chat,
    render_turn_analysis,
)
from edd_agent_lab.ui.layout import load_css, page_shell, sidebar_brand

LAB_CONSOLE_PORT = 8502


def _process_turn(
    message: str,
    scenario_id: str,
    suite_id: str,
    left_version: str,
    right_version: str,
) -> None:
    import streamlit as st

    turns: list[dict[str, str]] = list(st.session_state.turns)
    left_history = build_side_history(turns, "left")
    right_history = build_side_history(turns, "right")

    with st.spinner("Running both agent versions..."):
        left = run_customer_solution_turn(
            scenario_id=scenario_id,
            agent_version=left_version,
            user_message=message,
            conversation_history=left_history,
        )
        right = run_customer_solution_turn(
            scenario_id=scenario_id,
            agent_version=right_version,
            user_message=message,
            conversation_history=right_history,
        )

    turns.append(
        {
            "user": message,
            "left_response": left["final_response"],
            "right_response": right["final_response"],
        }
    )
    st.session_state.turns = turns
    st.session_state.turn_count += 1

    evaluation = evaluate_turn(
        agent="customer_solution_agent",
        scenario_id=scenario_id,
        suite_id=suite_id,
        user_input=message,
        responses_by_version={
            left_version: left["final_response"],
            right_version: right["final_response"],
        },
    )
    comparison = compare_turn_evaluation(
        evaluation,
        before_version=left_version,
        after_version=right_version,
    )
    turn_id = new_turn_id()
    artifact_dir = write_turn_artifacts(
        session_id=st.session_state.session_id,
        turn_id=turn_id,
        evaluation=evaluation,
        comparison=comparison,
    )
    st.session_state.latest_evaluation = evaluation
    st.session_state.latest_comparison = comparison
    st.session_state.latest_artifact_dir = str(artifact_dir)


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="EDD Agent Lab — Side-by-Side",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_css()
    init_session_defaults()
    sidebar_brand()

    scenarios = list_scenario_ids("customer-solution")
    suites = list_eval_suite_ids("customer-solution")
    version_options = ["v0-baseline", "v1-discovery-graph", "v3-competency-model"]

    with st.sidebar:
        st.markdown("### Run setup")
        st.selectbox("Scenario", scenarios, key="scenario_id")
        st.selectbox("Eval suite", suites, key="suite_id")
        st.selectbox("Left version", version_options, key="left_version")
        st.selectbox("Right version", version_options, key="right_version")
        st.divider()
        st.markdown("### Session")
        st.caption(st.session_state.session_id)
        st.caption(f"Turns: {st.session_state.turn_count}")
        gen_mode = resolve_generation_mode()
        st.caption(f"Generation: {gen_mode}")
        if gen_mode == "mock":
            st.caption("Set OPENAI_API_KEY + AGENT_GENERATION_MODE=auto for live replies.")
        if st.button("Clear chat", use_container_width=True):
            st.session_state.turns = []
            st.session_state.latest_evaluation = None
            st.session_state.latest_comparison = None
            st.session_state.latest_artifact_dir = None
            st.session_state.turn_count = 0
            st.rerun()
        if st.button("Send scenario as first message", use_container_width=True):
            scenario = load_scenario("customer-solution", st.session_state.scenario_id)
            st.session_state.pending_message = scenario.problem
            st.rerun()
        st.divider()
        st.caption("Platform UI: :8501 · Lab chat: :8502")

    scenario_id = st.session_state.scenario_id
    suite_id = st.session_state.suite_id
    left_version = st.session_state.left_version
    right_version = st.session_state.right_version

    page_shell(
        "Side-by-Side Agent Chat",
        f"{left_version} vs {right_version} · multi-turn · same prompt to both columns",
    )

    evaluation = st.session_state.get("latest_evaluation")
    left_result = None
    right_result = None
    if evaluation:
        by_version = {item.agent_version: item for item in evaluation.versions}
        left_result = by_version.get(left_version)
        right_result = by_version.get(right_version)

    render_side_by_side_chat(
        st.session_state.turns,
        left_version,
        right_version,
        left_result=left_result,
        right_result=right_result,
    )

    comparison = st.session_state.get("latest_comparison")
    if evaluation and comparison:
        render_turn_analysis(comparison, evaluation)
    render_artifacts_panel(st.session_state.get("latest_artifact_dir"), evaluation)

    pending = st.session_state.pop("pending_message", None)
    if pending:
        _process_turn(
            message=pending.strip(),
            scenario_id=scenario_id,
            suite_id=suite_id,
            left_version=left_version,
            right_version=right_version,
        )
        st.rerun()

    prompt = st.chat_input("Message both agents…")
    if prompt:
        _process_turn(
            message=prompt.strip(),
            scenario_id=scenario_id,
            suite_id=suite_id,
            left_version=left_version,
            right_version=right_version,
        )
        st.rerun()


if __name__ == "__main__":
    main()
