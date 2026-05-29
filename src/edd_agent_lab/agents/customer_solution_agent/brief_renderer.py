"""Render the structured discovery brief from agent state."""

from __future__ import annotations

from edd_agent_lab.evals.schemas import Scenario

from .state import CustomerSolutionState


def render_discovery_brief(
    state: CustomerSolutionState,
    scenario: Scenario,
    *,
    include_competencies: bool = False,
) -> str:
    questions = "\n".join(
        f"- {item.question} ({item.reason})" for item in state.discovery_questions
    )
    metrics = "\n".join(
        f"- {item.metric}: {item.why_it_matters} Measurement: {item.how_to_measure}"
        for item in state.success_metrics
    )
    risks = "\n".join(f"- {item.risk} Mitigation: {item.mitigation}" for item in state.risks)
    stakeholders = "\n".join(f"- {item}" for item in state.stakeholders) or "- TBD"
    assumptions = "\n".join(f"- {item}" for item in state.assumptions) or "- TBD"

    competency_section = ""
    if include_competencies and state.discovery_competencies:
        competency_lines = "\n".join(f"- {item}" for item in state.discovery_competencies)
        competency_section = (
            "## Discovery Competencies (Domain-Neutral Framework)\n"
            f"{competency_lines}\n\n"
        )

    return (
        f"# Customer Solution Discovery Brief — {scenario.title}\n\n"
        "## Problem Summary\n"
        f"{state.problem_summary}\n\n"
        f"{competency_section}"
        "## Clarifying Discovery Questions\n"
        f"{questions}\n\n"
        "## Workflow Decomposition\n"
        f"{state.workflow_summary or 'Workflow details to be confirmed.'}\n\n"
        "## Stakeholder Map\n"
        f"{stakeholders}\n\n"
        "## Data and Integration Assumptions\n"
        f"{assumptions}\n\n"
        "## Proposed Solution\n"
        f"{state.proposed_solution}\n\n"
        "## Success Metrics\n"
        f"{metrics}\n\n"
        "## Risks and Mitigations\n"
        f"{risks}\n\n"
        "## Pilot Plan\n"
        f"{state.pilot_plan}\n\n"
        "## Evaluation Plan\n"
        f"{state.eval_plan}\n"
    )
