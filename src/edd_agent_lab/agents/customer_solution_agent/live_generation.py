"""OpenAI-backed discovery state and chat response generation."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from edd_agent_lab.agents.generation import get_chat_model
from edd_agent_lab.evals.schemas import Scenario

from .competency import DISCOVERY_COMPETENCIES
from .prompts import (
    chat_response_system_prompt,
    chat_response_user_prompt,
    discovery_draft_system_prompt,
    discovery_draft_user_prompt,
)
from .state import CustomerSolutionState, DiscoveryQuestion, Risk, SuccessMetric

ChatMessage = dict[str, str]


class LiveDiscoveryDraft(BaseModel):
    problem_summary: str
    discovery_questions: list[DiscoveryQuestion] = Field(default_factory=list)
    workflow_summary: str | None = None
    stakeholders: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    proposed_solution: str | None = None
    success_metrics: list[SuccessMetric] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    pilot_plan: str | None = None
    eval_plan: str | None = None
    discovery_competencies: list[str] = Field(default_factory=list)


def generate_discovery_draft(
    scenario: Scenario,
    agent_version: str,
    user_problem: str,
) -> LiveDiscoveryDraft:
    model = get_chat_model(temperature=0.1).with_structured_output(LiveDiscoveryDraft)
    system = discovery_draft_system_prompt(agent_version)
    user = discovery_draft_user_prompt(scenario, user_problem, agent_version=agent_version)
    draft = model.invoke(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    if not isinstance(draft, LiveDiscoveryDraft):
        draft = LiveDiscoveryDraft.model_validate(draft)

    if agent_version == "v3-competency-model" and not draft.discovery_competencies:
        draft.discovery_competencies = list(DISCOVERY_COMPETENCIES)
    return draft


def apply_discovery_draft(
    draft: LiveDiscoveryDraft,
    *,
    scenario_id: str,
    user_problem: str,
    conversation_history: list[ChatMessage] | None,
) -> CustomerSolutionState:
    return CustomerSolutionState(
        scenario_id=scenario_id,
        user_problem=user_problem,
        problem_summary=draft.problem_summary,
        discovery_questions=draft.discovery_questions,
        workflow_summary=draft.workflow_summary,
        stakeholders=draft.stakeholders,
        assumptions=draft.assumptions,
        proposed_solution=draft.proposed_solution,
        success_metrics=draft.success_metrics,
        risks=draft.risks,
        pilot_plan=draft.pilot_plan,
        eval_plan=draft.eval_plan,
        discovery_competencies=draft.discovery_competencies,
        messages=list(conversation_history or []),
    )


def generate_live_chat_response(
    state: CustomerSolutionState,
    scenario: Scenario,
    *,
    user_message: str,
    conversation_history: list[ChatMessage] | None,
    agent_version: str,
) -> str:
    model = get_chat_model(temperature=0.3)
    state_payload = {
        "problem_summary": state.problem_summary,
        "discovery_questions": [item.model_dump() for item in state.discovery_questions],
        "workflow_summary": state.workflow_summary,
        "stakeholders": state.stakeholders,
        "assumptions": state.assumptions,
        "proposed_solution": state.proposed_solution,
        "success_metrics": [item.model_dump() for item in state.success_metrics],
        "risks": [item.model_dump() for item in state.risks],
        "pilot_plan": state.pilot_plan,
        "eval_plan": state.eval_plan,
        "discovery_competencies": state.discovery_competencies,
    }
    system = chat_response_system_prompt(agent_version)
    user = chat_response_user_prompt(
        scenario,
        user_message,
        json.dumps(state_payload, indent=2),
        conversation_history,
    )
    answer = model.invoke(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    content = getattr(answer, "content", answer)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Live chat generation returned an empty response.")
    return content.strip()


def generate_live_brief_response(
    state: CustomerSolutionState,
    scenario: Scenario,
    agent_version: str,
) -> str:
    include_competencies = agent_version == "v3-competency-model"
    from .brief_renderer import render_discovery_brief

    return render_discovery_brief(
        state,
        scenario,
        include_competencies=include_competencies,
    )
