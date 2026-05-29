"""Graph nodes for customer solution agent versions."""

from __future__ import annotations

from edd_agent_lab.evals.schemas import Scenario

from .brief_renderer import render_discovery_brief
from .competency import (
    DISCOVERY_COMPETENCIES,
    competency_problem_summary,
    competency_vocabulary,
)
from .state import CustomerSolutionState, DiscoveryQuestion, Risk, SuccessMetric


def apply_competency_model_node(
    state: CustomerSolutionState, scenario: Scenario
) -> CustomerSolutionState:
    state.discovery_competencies = list(DISCOVERY_COMPETENCIES)
    state.problem_summary = competency_problem_summary(scenario)
    vocab = competency_vocabulary(scenario)
    state.discovery_questions = [
        DiscoveryQuestion(
            question=f"What evidence do we need for '{theme}' before proposing a solution?",
            reason="Tie each discovery question to scenario-specific competency themes.",
        )
        for theme in scenario.expected_themes
    ]
    state.workflow_summary = (
        f"Competency-aligned workflow for {scenario.domain}: intake -> triage -> analysis -> "
        f"human validation -> action -> audit logging. Scenario focus areas include "
        f"{', '.join(vocab[:5])}."
    )
    state.assumptions = [
        "Discovery competencies are applied before solution design.",
        f"Pilot instrumentation must capture evidence for: {', '.join(vocab[:4])}.",
    ]
    return state


def intake_node(state: CustomerSolutionState) -> CustomerSolutionState:
    summary = (
        "Customer needs an AI-assisted discovery and delivery plan "
        "for the stated business problem. "
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


# v0 node
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
            mitigation=(
                "Require human review for high-impact actions "
                "and confidence-based escalation."
            ),
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


def clarify_problem_node(state: CustomerSolutionState, scenario: Scenario) -> CustomerSolutionState:
    state.problem_summary = (
        f"The customer needs to improve a {scenario.domain} process with AI while balancing "
        "operational impact, risk controls, and measurable outcomes."
    )
    state.discovery_questions = [
        DiscoveryQuestion(
            question="Which part of the current workflow creates the highest cost or delay?",
            reason="Defines the pilot boundary and business leverage.",
        ),
        DiscoveryQuestion(
            question="What decision points require human review before action is taken?",
            reason="Prevents unsafe automation and clarifies guardrail design.",
        ),
        DiscoveryQuestion(
            question="Which systems are source-of-truth and what data quality gaps exist?",
            reason="Determines technical feasibility and integration order.",
        ),
        DiscoveryQuestion(
            question="What baseline KPI threshold must improve for the pilot to be accepted?",
            reason="Anchors delivery to measurable value.",
        ),
    ]
    return state


def identify_workflow_node(
    state: CustomerSolutionState, scenario: Scenario
) -> CustomerSolutionState:
    state.workflow_summary = (
        f"Target workflow in {scenario.domain}: step-by-step intake -> "
        "triage -> analysis -> human validation "
        "-> action/communication -> audit logging."
    )
    state.assumptions.extend(
        [
            "A single pilot workflow can be isolated without broad process redesign.",
            "Current-state baseline metrics can be captured before intervention.",
        ]
    )
    return state


def identify_stakeholders_node(
    state: CustomerSolutionState, scenario: Scenario
) -> CustomerSolutionState:
    by_domain = {
        "healthcare": ["Clinicians", "Compliance", "IT", "Operations"],
        "legal": ["Partners", "Associates", "Knowledge Management", "Security"],
        "banking": ["Fraud Ops", "Compliance", "Model Risk", "Engineering"],
        "manufacturing": ["Plant Operations", "Maintenance", "Quality", "IT"],
        "hr": ["HR", "Legal", "Employee Experience", "Security"],
        "customer_support": ["Support Ops", "Specialists", "Platform Engineering", "Product"],
    }
    state.stakeholders = by_domain.get(
        scenario.domain,
        ["Business Owner", "Operations", "IT", "Compliance"],
    )
    return state


def identify_stakeholders_competency_node(
    state: CustomerSolutionState, scenario: Scenario
) -> CustomerSolutionState:
    identify_stakeholders_node(state, scenario)
    vocab = competency_vocabulary(scenario)
    for term in vocab[:4]:
        label = term.replace("_", " ").title()
        if label not in state.stakeholders:
            state.stakeholders.append(f"{label} (theme owner)")
    return state


def define_success_metrics_node(
    state: CustomerSolutionState, scenario: Scenario
) -> CustomerSolutionState:
    state.success_metrics = [
        SuccessMetric(
            metric="Cycle time reduction",
            why_it_matters="Primary customer value is faster completion of the target workflow.",
            how_to_measure="Compare median task completion time pre/post pilot.",
        ),
        SuccessMetric(
            metric="Quality and risk adherence",
            why_it_matters="Improvement must preserve quality and governance outcomes.",
            how_to_measure="Track QA pass rate and policy exception rate per 100 cases.",
        ),
        SuccessMetric(
            metric="Adoption in target user cohort",
            why_it_matters="Business impact requires real operational usage.",
            how_to_measure="Measure weekly active pilot users and assist utilization.",
        ),
    ]
    state.assumptions.append(f"Metrics are feasible to instrument in {scenario.domain} systems.")
    return state


def propose_solution_node(
    state: CustomerSolutionState, scenario: Scenario
) -> CustomerSolutionState:
    state.proposed_solution = (
        f"Deploy a discovery-first {scenario.domain} copilot that structures intake, provides "
        "context-aware recommendations, highlights uncertainty, and routes high-risk cases to "
        "human reviewers with audit trails."
    )
    return state


def review_risks_node(state: CustomerSolutionState, scenario: Scenario) -> CustomerSolutionState:
    state.risks = [
        Risk(
            risk="Incorrect recommendations on high-impact cases.",
            mitigation=(
                "Enforce confidence thresholds, mandatory human review, "
                "and escalation paths."
            ),
        ),
        Risk(
            risk="Workflow disruption from weak integration and handoffs.",
            mitigation=(
                "Start with one bounded integration path and monitor "
                "drop-off/failure points."
            ),
        ),
        Risk(
            risk=f"Domain-specific governance gaps for {scenario.domain}.",
            mitigation="Map policy controls to each workflow stage before pilot launch.",
        ),
    ]
    return state


def review_risks_competency_node(
    state: CustomerSolutionState, scenario: Scenario
) -> CustomerSolutionState:
    review_risks_node(state, scenario)
    for theme in scenario.expected_themes[:2]:
        state.risks.append(
            Risk(
                risk=f"Competency gap if '{theme}' is not validated before pilot launch.",
                mitigation=(
                    "Add explicit checklist evidence for this theme in weekly "
                    "discovery reviews."
                ),
            )
        )
    return state


def create_pilot_plan_node(state: CustomerSolutionState) -> CustomerSolutionState:
    state.pilot_plan = (
        "Run a 4-6 week pilot on one bounded workflow segment with named owners, "
        "weekly reviews, and go/no-go gates tied to KPI and risk thresholds."
    )
    return state


def create_eval_plan_node(state: CustomerSolutionState) -> CustomerSolutionState:
    state.eval_plan = (
        "Run discovery_quality, measurable_value, and risk_review suites each iteration. "
        "Require score improvement versus prior run and no "
        "critical risk-regression before promotion."
    )
    return state


def final_response_node(
    state: CustomerSolutionState, scenario: Scenario, *, include_competencies: bool = False
) -> CustomerSolutionState:
    state.final_response = render_discovery_brief(
        state,
        scenario,
        include_competencies=include_competencies,
    )
    return state
