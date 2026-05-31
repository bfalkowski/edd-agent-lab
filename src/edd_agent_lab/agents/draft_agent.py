"""Generic runnable draft agents for local builder workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class DraftAgentState(BaseModel):
    agent_key: str
    agent_version: str
    target: dict[str, Any]
    scenario: dict[str, Any]
    graph_design: dict[str, Any]
    generation_mode: Literal["mock", "live"] = "mock"
    tool_mode: str = "local_draft"
    problem_summary: str = ""
    missing_context: list[str] = Field(default_factory=list)
    grounded_actions: list[str] = Field(default_factory=list)
    node_trace: list[str] = Field(default_factory=list)
    final_response: str = ""


@dataclass(frozen=True)
class DraftAgentRun:
    final_response: str
    state: DraftAgentState


def run_draft_agent(
    *,
    agent_key: str,
    agent_version: str,
    target: dict[str, Any],
    scenario: dict[str, Any],
    graph_design: dict[str, Any],
    generation_mode: Literal["mock", "live"] = "mock",
) -> DraftAgentRun:
    graph = _build_graph(graph_design)
    initial_state = DraftAgentState(
        agent_key=agent_key,
        agent_version=agent_version,
        target=target,
        scenario=scenario,
        graph_design=graph_design,
        generation_mode=generation_mode,
    )
    final_state = DraftAgentState.model_validate(graph.invoke(initial_state))
    return DraftAgentRun(final_response=final_state.final_response, state=final_state)


def _build_graph(graph_design: dict[str, Any]):
    node_ids = _ordered_node_ids(graph_design)
    graph = StateGraph(DraftAgentState)

    for node_id in node_ids:
        graph.add_node(node_id, _node_for(node_id))

    first_node, *remaining_nodes = node_ids
    graph.add_edge(START, first_node)
    previous_node = first_node
    for node_id in remaining_nodes:
        graph.add_edge(previous_node, node_id)
        previous_node = node_id
    graph.add_edge(previous_node, END)
    return graph.compile()


def _ordered_node_ids(graph_design: dict[str, Any]) -> list[str]:
    node_ids = [
        str(node.get("id"))
        for node in graph_design.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    ]
    if node_ids:
        return node_ids
    return ["understand_request", "draft_response"]


def _node_for(node_id: str):
    nodes = {
        "understand_request": _understand_request,
        "collect_domain_context": _collect_domain_context,
        "plan_grounded_next_actions": _plan_grounded_next_actions,
        "draft_response": _draft_response,
    }
    return nodes.get(node_id, _passthrough_node(node_id))


def _understand_request(state: DraftAgentState) -> DraftAgentState:
    scenario_problem = state.scenario.get("problem", "")
    target_purpose = state.target.get("purpose", "")
    state.problem_summary = (
        f"The request is to use {state.target.get('name', state.agent_key)} for: "
        f"{scenario_problem}"
    )
    state.missing_context = [
        "Source material or records the agent should inspect.",
        "User constraints, risk tolerance, and required output format.",
        "Examples of acceptable and unacceptable recommendations.",
    ]
    if target_purpose:
        state.node_trace.append(f"understand_request: scoped to {target_purpose}")
    else:
        state.node_trace.append("understand_request")
    return state


def _collect_domain_context(state: DraftAgentState) -> DraftAgentState:
    state.node_trace.append("collect_domain_context")
    if "Domain facts that connect the scenario to safe next actions." not in state.missing_context:
        state.missing_context.append("Domain facts that connect the scenario to safe next actions.")
    return state


def _plan_grounded_next_actions(state: DraftAgentState) -> DraftAgentState:
    state.node_trace.append("plan_grounded_next_actions")
    state.grounded_actions = [
        "Gather the missing context before making final recommendations.",
        "Map each recommendation to available evidence or an explicit assumption.",
        "Keep unsupported claims in an assumptions section.",
        "Treat missing production tools as a readiness blocker, not as success.",
    ]
    return state


def _draft_response(state: DraftAgentState) -> DraftAgentState:
    state.node_trace.append("draft_response")
    if state.grounded_actions:
        actions = state.grounded_actions
        heading = f"# {state.target.get('name', state.agent_key)} v1 draft"
        intro = (
            "The request is in scope for this draft agent, but the answer should remain "
            "grounded in source material and constraints that are not fully wired yet."
        )
    else:
        actions = [
            "Confirm the user, workflow, and decision this agent should support.",
            "Add representative scenarios and expected behavior themes.",
            "Review the generated rules, eval contract, information needs, and tool blockers.",
            "Run v1 only after the graph design and tool assumptions are explicit.",
        ]
        heading = f"# {state.target.get('name', state.agent_key)} v0 baseline"
        intro = "I can help with this, but this draft v0 has no tools or domain evidence wired yet."

    state.final_response = "\n".join(
        [
            heading,
            "",
            f"**Target purpose:** {state.target.get('purpose', '')}",
            "",
            f"**Scenario:** {state.scenario.get('problem', '')}",
            "",
            "## What I can say now",
            intro,
            "",
            "## Missing context to collect",
            *[f"- {item}" for item in state.missing_context],
            "",
            "## Safe next actions",
            *[f"- {item}" for item in actions],
        ]
    )
    return state


def _passthrough_node(node_id: str):
    def node(state: DraftAgentState) -> DraftAgentState:
        state.node_trace.append(node_id)
        return state

    return node
