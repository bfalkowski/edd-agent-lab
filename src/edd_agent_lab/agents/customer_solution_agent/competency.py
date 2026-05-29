"""Domain-neutral discovery competency framework (Milestone 6)."""

from __future__ import annotations

from edd_agent_lab.evals.schemas import Scenario
from edd_agent_lab.evals.scoring import discovery_theme_patterns

DISCOVERY_COMPETENCIES: tuple[str, ...] = (
    "Business objective and constraints",
    "Workflow decomposition",
    "Stakeholders and decision rights",
    "Data and integration assumptions",
    "Compliance and policy controls",
    "Adoption and change management",
    "Measurable success metrics",
    "Evaluation and verification plan",
)


def competency_vocabulary(scenario: Scenario) -> list[str]:
    return discovery_theme_patterns(scenario)


def competency_problem_summary(scenario: Scenario) -> str:
    vocab = ", ".join(competency_vocabulary(scenario)[:6])
    return (
        f"The customer needs a disciplined discovery plan for {scenario.title} "
        f"({scenario.domain}). Competency coverage must remain explicit across "
        f"business objective, workflow, stakeholders, data, compliance, adoption, "
        f"metrics, and evaluation. Scenario signals: {vocab}."
    )
