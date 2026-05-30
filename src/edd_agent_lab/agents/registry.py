"""Agent key normalization and run dispatch."""

from __future__ import annotations

from typing import Any

AGENT_DIR_ALIASES: dict[str, str] = {
    "customer-solution": "customer_solution_agent",
    "customer_solution": "customer_solution_agent",
    "customer_solution_agent": "customer_solution_agent",
    "customer-escalation-triage": "customer_escalation_triage",
    "customer_escalation_triage": "customer_escalation_triage",
    "customer_escalation_triage_agent": "customer_escalation_triage",
}

ESCALATION_AGENT_DIRS = frozenset({"customer_escalation_triage"})


def normalize_agent_dir(agent_key: str) -> str:
    return AGENT_DIR_ALIASES.get(agent_key, agent_key.replace("-", "_"))


def is_escalation_agent(agent_key: str) -> bool:
    return normalize_agent_dir(agent_key) in ESCALATION_AGENT_DIRS


def run_agent(
    *,
    scenario_id: str,
    agent_key: str,
    agent_version: str,
    generation_mode: str | None = None,
    **kwargs: Any,
) -> Any:
    if is_escalation_agent(agent_key):
        from edd_agent_lab.agents.customer_escalation_triage.runner import (
            run_customer_escalation_triage,
        )

        return run_customer_escalation_triage(
            scenario_id=scenario_id,
            agent_key=agent_key,
            agent_version=agent_version,
            generation_mode=generation_mode,
        )

    from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_agent

    return run_customer_solution_agent(
        scenario_id=scenario_id,
        agent_key=agent_key,
        agent_version=agent_version,
        generation_mode=generation_mode,
        **kwargs,
    )
