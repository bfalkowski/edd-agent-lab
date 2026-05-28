"""Runner for Customer Solution Discovery Agent v0."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from edd_agent_lab.paths import LAB_RUNS_DIR
from edd_agent_lab.scenarios.loading import load_scenario

from .graph import build_graph
from .state import CustomerSolutionState


@dataclass
class AgentRunResult:
    run_id: str
    agent: str
    agent_version: str
    scenario_id: str
    output_path: Path
    final_response: str
    state: CustomerSolutionState


def run_customer_solution_agent(
    scenario_id: str,
    agent_key: str = "customer-solution",
    agent_version: str = "v0-baseline",
) -> AgentRunResult:
    scenario = load_scenario(agent_key=agent_key, scenario_id=scenario_id)

    graph = build_graph(scenario)
    initial_state = CustomerSolutionState(
        scenario_id=scenario.id,
        user_problem=scenario.problem,
    )
    final_state = graph.invoke(initial_state)
    final_model = CustomerSolutionState.model_validate(final_state)

    run_id = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    output_path = _write_run_artifact(
        run_id=run_id,
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        agent_version=agent_version,
        state=final_model,
    )
    return AgentRunResult(
        run_id=run_id,
        agent="customer_solution_agent",
        agent_version=agent_version,
        scenario_id=scenario.id,
        output_path=output_path,
        final_response=final_model.final_response or "",
        state=final_model,
    )


def _write_run_artifact(
    run_id: str,
    scenario_id: str,
    scenario_title: str,
    agent_version: str,
    state: CustomerSolutionState,
) -> Path:
    out_dir = LAB_RUNS_DIR / "customer_solution_agent" / agent_version
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"run-{run_id}-{scenario_id}.json"

    payload = {
        "run_id": run_id,
        "agent": "customer_solution_agent",
        "agent_version": agent_version,
        "scenario": {"id": scenario_id, "title": scenario_title},
        "response": {
            "problem_summary": state.problem_summary,
            "discovery_questions": [q.model_dump() for q in state.discovery_questions],
            "proposed_solution": state.proposed_solution,
            "success_metrics": [m.model_dump() for m in state.success_metrics],
            "risks": [r.model_dump() for r in state.risks],
            "pilot_plan": state.pilot_plan,
            "eval_plan": state.eval_plan,
            "final_response": state.final_response,
        },
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
