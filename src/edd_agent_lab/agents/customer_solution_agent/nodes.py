"""v0 graph nodes: intake -> solution brief -> final response."""

from __future__ import annotations

from edd_agent_lab.evals.schemas import Scenario

from .state import CustomerSolutionState, DiscoveryQuestion, Risk, SuccessMetric


def intake_node(state: CustomerSolutionState) -> CustomerSolutionState:
    summary = (
        "Customer needs an AI-assisted discovery and delivery plan for the stated business problem. "
        "The first objective is to clarify constraints and define measurable outcomes."
    )
    state.problem_summary = summary
    state.discovery_questions = [
        DiscoveryQuestion(
            question="Which workflow step creates the largest burden today?",
            reason="Find the highest-leverage pilot scope.",
        ),
        DiscoveryQuestion(
            question="What compliance or policy controls must any AI output satisfy?",
            reason="Ensure feasibility and safety before solution design.",
        ),
        DiscoveryQuestion(
            question="What baseline metric is available today (time, quality, or throughput)?",
            reason="Enable measurable before/after verification.",
        ),
    ]
    return state


def solution_brief_node(state: CustomerSolutionState, scenario: Scenario) -> CustomerSolutionState:
    state.proposed_solution = (
        f"Build a domain-specific copilot for {scenario.domain} that assists the target workflow, "
        "surfaces grounded recommendations, and routes uncertain cases to human reviewers."
    )
    state.success_metrics = [
        SuccessMetric(
            metric="Cycle time reduction",
            why_it_matters="Primary business value is faster workflow completion.",
            how_to_measure="Compare median end-to-end task time before and after pilot rollout.",
        ),
        SuccessMetric(
            metric="Quality and safety score",
            why_it_matters="Speed must not degrade outcomes or compliance quality.",
            how_to_measure="Track QA review pass rate and critical error rate per 100 tasks.",
        ),
        SuccessMetric(
            metric="Adoption by frontline users",
            why_it_matters="Sustained impact requires behavior change, not one-time usage.",
            how_to_measure="Measure weekly active users and task-assist utilization rate.",
        ),
    ]
    state.risks = [
        Risk(
            risk="Incorrect or low-confidence recommendations in sensitive workflows.",
            mitigation="Require human review for high-impact actions and confidence-based escalation.",
        ),
        Risk(
            risk="Poor integration with existing systems causing workflow friction.",
            mitigation="Start with one bounded pilot workflow and instrument handoff failures.",
        ),
        Risk(
            risk="Weak change management reduces adoption despite technical quality.",
            mitigation="Run enablement sessions and collect role-specific feedback each sprint.",
        ),
    ]
    state.pilot_plan = (
        "Pilot one workflow for 4-6 weeks with a defined user cohort, baseline metrics, "
        "weekly risk reviews, and go/no-go criteria tied to metric targets."
    )
    state.eval_plan = (
        "Evaluate discovery quality, measurable value, and risk coverage on each run. "
        "Accept changes only when eval evidence improves against baseline."
    )
    return state


def final_response_node(state: CustomerSolutionState, scenario: Scenario) -> CustomerSolutionState:
    questions = "\n".join(
        f"- {item.question} ({item.reason})" for item in state.discovery_questions
    )
    metrics = "\n".join(
        f"- {item.metric}: {item.why_it_matters} Measurement: {item.how_to_measure}"
        for item in state.success_metrics
    )
    risks = "\n".join(f"- {item.risk} Mitigation: {item.mitigation}" for item in state.risks)

    state.final_response = (
        f"# Customer Solution Discovery Brief — {scenario.title}\n\n"
        "## Problem Summary\n"
        f"{state.problem_summary}\n\n"
        "## Discovery Questions\n"
        f"{questions}\n\n"
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
    return state
