"""Schemas for turn-level side-by-side console evaluation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TurnCheckResult(BaseModel):
    id: str
    score: float
    passed: bool
    comment: str
    evidence: list[str] = Field(default_factory=list)
    fix_hint: str | None = None


class TurnVersionResult(BaseModel):
    agent_version: str
    overall_score: float
    passed: bool
    checks: list[TurnCheckResult] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class TurnEvaluation(BaseModel):
    agent: str
    scenario_id: str
    suite_id: str
    user_input: str
    versions: list[TurnVersionResult] = Field(default_factory=list)


class TurnComparison(BaseModel):
    before_version: str
    after_version: str
    before_score: float
    after_score: float
    score_delta: float
    decision: str
    improved_checks: list[str] = Field(default_factory=list)
    regressed_checks: list[str] = Field(default_factory=list)
    unchanged_checks: list[str] = Field(default_factory=list)
    explanation: str


class TurnSummary(BaseModel):
    turn_id: str
    user_input: str
    artifact_dir: str
    before_score: float
    after_score: float
    score_delta: float
    decision: str
