from typing import Literal

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    id: str
    title: str
    domain: str
    problem: str
    expected_themes: list[str] = Field(default_factory=list)


class EvalCheck(BaseModel):
    id: str
    type: Literal["llm_judge", "structure", "keyword"]
    weight: float = 1.0
    rubric: str | None = None
    patterns: list[str] = Field(default_factory=list)


class ScenarioRef(BaseModel):
    id: str
    scenario: str
    checks: list[EvalCheck] = Field(default_factory=list)


class EvalSuite(BaseModel):
    id: str
    agent: str
    description: str = ""
    cases: list[ScenarioRef] = Field(default_factory=list)


class OverfittingVariant(BaseModel):
    id: str
    scenario: str
    mutation_type: str
    expected_invariant: str = ""


class OverfittingEvalSuite(BaseModel):
    id: str
    agent: str
    description: str = ""
    base_case: ScenarioRef
    variants: list[OverfittingVariant] = Field(default_factory=list)
