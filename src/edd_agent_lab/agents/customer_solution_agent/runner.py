"""Runner for Customer Solution Discovery Agent versions."""

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
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    scenario = load_scenario(agent_key=agent_key, scenario_id=scenario_id)

    graph = build_graph(scenario, agent_version=agent_version)
    initial_state = CustomerSolutionState(
        scenario_id=scenario.id,
        user_problem=scenario.problem,
    )
    final_state = graph.invoke(initial_state)
    final_model = CustomerSolutionState.model_validate(final_state)

    run_id = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    completed_at = run_id
    output_path = _write_run_artifact(
        run_id=run_id,
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        agent_version=agent_version,
        started_at=started_at,
        completed_at=completed_at,
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
    started_at: str,
    completed_at: str,
    state: CustomerSolutionState,
) -> Path:
    out_dir = LAB_RUNS_DIR / "customer_solution_agent" / agent_version
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"run-{run_id}-{scenario_id}.json"
    latest_output_path = out_dir / "agent-output.json"

    payload = {
        "run_id": run_id,
        "agent": "customer_solution_agent",
        "agent_version": agent_version,
        "suite": "agent_run",
        "scenario_ids": [scenario_id],
        "started_at": started_at,
        "completed_at": completed_at,
        "outputs": {
            scenario_id: {
                "problem_summary": state.problem_summary,
                "discovery_questions": [q.model_dump() for q in state.discovery_questions],
                "proposed_solution": state.proposed_solution,
                "success_metrics": [m.model_dump() for m in state.success_metrics],
                "risks": [r.model_dump() for r in state.risks],
                "pilot_plan": state.pilot_plan,
                "eval_plan": state.eval_plan,
                "final_response": state.final_response,
            }
        },
        "eval_summary": None,
        "failure_packet": None,
        "artifact_paths": {
            "timestamped_output": str(output_path),
            "latest_output": str(latest_output_path),
        },
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
    rendered = json.dumps(payload, indent=2)
    output_path.write_text(rendered, encoding="utf-8")
    latest_output_path.write_text(rendered, encoding="utf-8")
    return output_path
