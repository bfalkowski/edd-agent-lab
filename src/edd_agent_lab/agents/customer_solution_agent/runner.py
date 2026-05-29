"""Runner for Customer Solution Discovery Agent versions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    user_message: str | None = None,
    write_artifacts: bool = True,
) -> AgentRunResult:
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    scenario = load_scenario(agent_key=agent_key, scenario_id=scenario_id)
    user_problem = scenario.problem
    if user_message:
        user_problem = f"{scenario.problem.strip()}\n\nUser message:\n{user_message.strip()}"

    graph = build_graph(scenario, agent_version=agent_version)
    initial_state = CustomerSolutionState(
        scenario_id=scenario.id,
        user_problem=user_problem,
    )
    final_state = graph.invoke(initial_state)
    final_model = CustomerSolutionState.model_validate(final_state)

    run_id = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    completed_at = run_id
    if write_artifacts:
        output_path = _write_run_artifact(
            run_id=run_id,
            scenario_id=scenario.id,
            scenario_title=scenario.title,
            agent_version=agent_version,
            started_at=started_at,
            completed_at=completed_at,
            state=final_model,
        )
    else:
        output_path = Path()
    return AgentRunResult(
        run_id=run_id,
        agent="customer_solution_agent",
        agent_version=agent_version,
        scenario_id=scenario.id,
        output_path=output_path,
        final_response=final_model.final_response or "",
        state=final_model,
    )


def run_customer_solution_turn(
    scenario_id: str,
    agent_version: str,
    user_message: str | None = None,
    *,
    agent_key: str = "customer-solution",
    write_artifacts: bool = False,
) -> dict[str, Any]:
    result = run_customer_solution_agent(
        scenario_id=scenario_id,
        agent_key=agent_key,
        agent_version=agent_version,
        user_message=user_message,
        write_artifacts=write_artifacts,
    )
    return {
        "agent": result.agent,
        "agent_version": result.agent_version,
        "scenario_id": result.scenario_id,
        "final_response": result.final_response,
        "artifact_path": str(result.output_path) if result.output_path else None,
        "run_id": result.run_id,
    }


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
