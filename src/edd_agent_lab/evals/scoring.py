"""Check scoring: deterministic and optional LLM-as-judge."""

from __future__ import annotations

import os
from dataclasses import dataclass

from edd_agent_lab.evals.schemas import EvalCheck


@dataclass
class CheckScore:
    id: str
    score: float
    passed: bool
    comment: str
    weight: float
    method: str

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "score": self.score,
            "passed": self.passed,
            "comment": self.comment,
            "weight": self.weight,
            "method": self.method,
        }


def score_check(check: EvalCheck, response_text: str) -> CheckScore:
    if check.type in {"structure", "keyword"}:
        return _score_structure_or_keyword(check, response_text)

    if check.type == "llm_judge":
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            llm_score = _try_llm_judge(check, response_text, api_key)
            if llm_score is not None:
                return llm_score
        return _heuristic_judge(check, response_text)

    return CheckScore(
        id=check.id,
        score=0.0,
        passed=False,
        comment=f"Unsupported check type: {check.type}",
        weight=check.weight,
        method="unsupported",
    )


def weighted_case_score(scores: list[CheckScore]) -> float:
    total_weight = sum(item.weight for item in scores)
    if total_weight <= 0:
        return 0.0
    weighted_sum = sum(item.score * item.weight for item in scores)
    return weighted_sum / total_weight


def _score_structure_or_keyword(check: EvalCheck, response_text: str) -> CheckScore:
    lowered = response_text.lower()
    patterns = [p.lower() for p in check.patterns]
    if not patterns:
        return CheckScore(
            id=check.id,
            score=0.0,
            passed=False,
            comment="No patterns configured for deterministic check.",
            weight=check.weight,
            method="deterministic",
        )

    matches = sum(1 for pattern in patterns if pattern in lowered)
    ratio = matches / len(patterns)
    score = round(ratio, 3)
    passed = ratio >= 0.6
    return CheckScore(
        id=check.id,
        score=score,
        passed=passed,
        comment=f"Matched {matches}/{len(patterns)} expected patterns.",
        weight=check.weight,
        method="deterministic",
    )


def _heuristic_judge(check: EvalCheck, response_text: str) -> CheckScore:
    # Fallback for local runs without model keys.
    lowered = response_text.lower()
    proxy_signals = {
        "asks_clarifying_questions": ["discovery questions", "clarifying", "?"],
        "identifies_workflow": ["workflow", "step", "handoff"],
        "defines_success_metrics": ["success metrics", "measurement", "baseline"],
        "includes_risks": ["risk", "mitigation"],
    }
    expected = proxy_signals.get(check.id, ["##", "- "])
    matches = sum(1 for signal in expected if signal in lowered)
    ratio = matches / len(expected)
    score = round(min(1.0, 0.35 + 0.65 * ratio), 3)
    passed = score >= 0.65
    return CheckScore(
        id=check.id,
        score=score,
        passed=passed,
        comment="Heuristic judge fallback used (no LLM key or call unavailable).",
        weight=check.weight,
        method="heuristic",
    )


def _try_llm_judge(check: EvalCheck, response_text: str, api_key: str) -> CheckScore | None:
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        return None

    try:
        model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
        prompt = (
            "You are an eval judge. Score the response from 0.0 to 1.0 for the rubric.\n"
            "Return exactly one line in format: score=<float>; comment=<short reason>\n\n"
            f"Rubric:\n{check.rubric or 'No rubric'}\n\n"
            f"Response:\n{response_text}\n"
        )
        answer = model.invoke(prompt).content
        if not isinstance(answer, str):
            return None

        score = _parse_score(answer)
        if score is None:
            return None
        score = max(0.0, min(1.0, score))
        passed = score >= 0.65
        comment = answer.strip()[:240]
        return CheckScore(
            id=check.id,
            score=round(score, 3),
            passed=passed,
            comment=comment,
            weight=check.weight,
            method="llm_judge",
        )
    except Exception:
        return None


def _parse_score(text: str) -> float | None:
    for token in text.replace("\n", " ").split():
        if token.startswith("score="):
            try:
                return float(token.split("=", 1)[1].strip(";"))
            except ValueError:
                return None
    return None
