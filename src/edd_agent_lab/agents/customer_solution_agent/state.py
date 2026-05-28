"""State schema for the Customer Solution Discovery Agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DiscoveryQuestion(BaseModel):
    question: str
    reason: str


class Risk(BaseModel):
    risk: str
    mitigation: str


class SuccessMetric(BaseModel):
    metric: str
    why_it_matters: str
    how_to_measure: str


class CustomerSolutionState(BaseModel):
    scenario_id: str
    user_problem: str

    problem_summary: str | None = None
    discovery_questions: list[DiscoveryQuestion] = Field(default_factory=list)
    workflow_summary: str | None = None
    stakeholders: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    proposed_solution: str | None = None
    success_metrics: list[SuccessMetric] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    pilot_plan: str | None = None
    eval_plan: str | None = None
    final_response: str | None = None

    messages: list[dict[str, Any]] = Field(default_factory=list)
