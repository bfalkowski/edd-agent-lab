"""v0 LangGraph definition for customer solution agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from edd_agent_lab.evals.schemas import Scenario

from .nodes import final_response_node, intake_node, solution_brief_node
from .state import CustomerSolutionState


def build_graph(scenario: Scenario):
    graph = StateGraph(CustomerSolutionState)

    graph.add_node("intake", intake_node)
    graph.add_node("solution_brief", lambda state: solution_brief_node(state, scenario))
    graph.add_node("final_response", lambda state: final_response_node(state, scenario))

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "solution_brief")
    graph.add_edge("solution_brief", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()
