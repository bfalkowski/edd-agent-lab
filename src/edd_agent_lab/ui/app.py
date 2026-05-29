"""Streamlit side-by-side agent comparison console."""

from __future__ import annotations

from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_turn
from edd_agent_lab.evals.loading import list_eval_suite_ids
from edd_agent_lab.evals.turn_artifacts import new_turn_id, write_turn_artifacts
from edd_agent_lab.evals.turn_comparison import compare_turn_evaluation
from edd_agent_lab.evals.turn_evaluator import evaluate_turn
from edd_agent_lab.scenarios.loading import list_scenario_ids, load_scenario
from edd_agent_lab.ui.components import (
    init_session_defaults,
    render_artifacts_panel,
    render_chat_panel,
    render_turn_analysis,
)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="EDD Agent Lab Console", layout="wide")
    st.title("EDD Agent Lab — Side-by-Side Console")
    init_session_defaults()

    scenarios = list_scenario_ids("customer-solution")
    suites = list_eval_suite_ids("customer-solution")
    version_options = ["v0-baseline", "v1-discovery-graph", "v3-competency-model"]

    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        scenario_id = col1.selectbox("Scenario", scenarios, key="scenario_id")
        suite_id = col2.selectbox("Eval suite", suites, index=0, key="suite_id")
        left_version = col3.selectbox("Left version", version_options, key="left_version")
        right_version = col4.selectbox(
            "Right version", version_options, index=1, key="right_version"
        )

    user_input = st.text_area("Message", key="user_input", height=120)
    btn1, btn2, btn3 = st.columns(3)
    send = btn1.button("Send to Both", type="primary")
    use_scenario = btn2.button("Use Scenario Problem")
    clear = btn3.button("Clear Session")

    if clear:
        st.session_state.left_messages = []
        st.session_state.right_messages = []
        st.session_state.latest_evaluation = None
        st.session_state.latest_comparison = None
        st.session_state.latest_artifact_dir = None
        st.rerun()

    if use_scenario:
        scenario = load_scenario("customer-solution", scenario_id)
        st.session_state.user_input = scenario.problem
        st.rerun()

    if send:
        message = (user_input or "").strip()
        if not message:
            st.error("Enter a message or use the scenario problem.")
        else:
            left = run_customer_solution_turn(
                scenario_id=scenario_id,
                agent_version=left_version,
                user_message=message,
            )
            right = run_customer_solution_turn(
                scenario_id=scenario_id,
                agent_version=right_version,
                user_message=message,
            )
            st.session_state.left_messages.append({"role": "user", "content": message})
            st.session_state.right_messages.append({"role": "user", "content": message})
            st.session_state.left_messages.append(
                {"role": "assistant", "content": left["final_response"]}
            )
            st.session_state.right_messages.append(
                {"role": "assistant", "content": right["final_response"]}
            )

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

    left_col, right_col = st.columns(2)
    evaluation = st.session_state.get("latest_evaluation")
    left_result = None
    right_result = None
    if evaluation:
        by_version = {item.agent_version: item for item in evaluation.versions}
        left_result = by_version.get(left_version)
        right_result = by_version.get(right_version)

    with left_col:
        render_chat_panel(left_version, st.session_state.left_messages, left_result)
    with right_col:
        render_chat_panel(right_version, st.session_state.right_messages, right_result)

    comparison = st.session_state.get("latest_comparison")
    if evaluation and comparison:
        render_turn_analysis(comparison, evaluation)
    render_artifacts_panel(st.session_state.get("latest_artifact_dir"), evaluation)


if __name__ == "__main__":
    main()
