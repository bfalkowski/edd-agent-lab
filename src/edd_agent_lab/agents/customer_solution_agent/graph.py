"""LangGraph definitions for customer solution agent versions."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from edd_agent_lab.evals.schemas import Scenario

from .nodes import (
    clarify_problem_node,
    create_eval_plan_node,
    create_pilot_plan_node,
    define_success_metrics_node,
    final_response_node,
    identify_stakeholders_node,
    identify_workflow_node,
    intake_node,
    propose_solution_node,
    review_risks_node,
    solution_brief_node,
)
from .state import CustomerSolutionState


def build_graph(scenario: Scenario, agent_version: str = "v0-baseline"):
    if agent_version == "v1-discovery-graph":
        return _build_v1_graph(scenario)
    return _build_v0_graph(scenario)


def _build_v0_graph(scenario: Scenario):
    graph = StateGraph(CustomerSolutionState)

    graph.add_node("intake", intake_node)
    graph.add_node("solution_brief", lambda state: solution_brief_node(state, scenario))
    graph.add_node("final_response", lambda state: final_response_node(state, scenario))

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "solution_brief")
    graph.add_edge("solution_brief", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()


def _build_v1_graph(scenario: Scenario):
    graph = StateGraph(CustomerSolutionState)

    graph.add_node("intake", intake_node)
    graph.add_node("clarify_problem", lambda state: clarify_problem_node(state, scenario))
    graph.add_node("identify_workflow", lambda state: identify_workflow_node(state, scenario))
    graph.add_node(
        "identify_stakeholders", lambda state: identify_stakeholders_node(state, scenario)
    )
    graph.add_node(
        "define_success_metrics", lambda state: define_success_metrics_node(state, scenario)
    )
    graph.add_node("propose_solution", lambda state: propose_solution_node(state, scenario))
    graph.add_node("review_risks", lambda state: review_risks_node(state, scenario))
    graph.add_node("create_pilot_plan", create_pilot_plan_node)
    graph.add_node("create_eval_plan", create_eval_plan_node)
    graph.add_node("final_response", lambda state: final_response_node(state, scenario))

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "clarify_problem")
    graph.add_edge("clarify_problem", "identify_workflow")
    graph.add_edge("identify_workflow", "identify_stakeholders")
    graph.add_edge("identify_stakeholders", "define_success_metrics")
    graph.add_edge("define_success_metrics", "propose_solution")
    graph.add_edge("propose_solution", "review_risks")
    graph.add_edge("review_risks", "create_pilot_plan")
    graph.add_edge("create_pilot_plan", "create_eval_plan")
    graph.add_edge("create_eval_plan", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()
