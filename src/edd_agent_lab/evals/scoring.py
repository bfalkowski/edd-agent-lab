"""Check scoring: deterministic and optional LLM-as-judge."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from edd_agent_lab.evals.schemas import EvalCheck, Scenario

_THEME_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "and",
        "before",
        "define",
        "decompose",
        "discuss",
        "identify",
        "include",
        "into",
        "map",
        "metrics",
        "propose",
        "risks",
        "surface",
        "their",
        "through",
        "with",
        "without",
        "workflow",
        "workflows",
    }
)

_CORE_DISCOVERY_SIGNALS = (
    "workflow",
    "stakeholder",
    "success metric",
    "risk",
    "evaluation plan",
    "pilot",
)


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


def discovery_theme_patterns(scenario: Scenario) -> list[str]:
    patterns: list[str] = [scenario.domain]
    for theme in scenario.expected_themes:
        for word in re.findall(r"[a-z]{5,}", theme.lower()):
            if word not in _THEME_STOPWORDS:
                patterns.append(word)
    unique: list[str] = []
    for pattern in patterns:
        if pattern not in unique:
            unique.append(pattern)
    return unique


def score_discovery_invariant(scenario: Scenario, response_text: str) -> CheckScore:
    """Score whether a variant response reflects scenario-specific discovery themes."""
    lowered = response_text.lower()
    theme_patterns = discovery_theme_patterns(scenario)
    theme_matches = sum(1 for pattern in theme_patterns if pattern in lowered)
    theme_ratio = theme_matches / len(theme_patterns) if theme_patterns else 0.0

    core_matches = sum(1 for signal in _CORE_DISCOVERY_SIGNALS if signal in lowered)
    core_ratio = core_matches / len(_CORE_DISCOVERY_SIGNALS)

    score = round(min(1.0, 0.45 * theme_ratio + 0.55 * core_ratio), 3)
    passed = theme_ratio >= 0.55 and core_ratio >= 0.85
    return CheckScore(
        id="discovery_discipline_invariant",
        score=score,
        passed=passed,
        comment=(
            f"Theme coverage {theme_matches}/{len(theme_patterns)}; "
            f"core discovery coverage {core_matches}/{len(_CORE_DISCOVERY_SIGNALS)}."
        ),
        weight=1.0,
        method="theme_invariant",
    )


def _heuristic_judge(check: EvalCheck, response_text: str) -> CheckScore:
    # Fallback for local runs without model keys.
    lowered = response_text.lower()
    proxy_signals = {
        "asks_clarifying_questions": ["discovery questions", "clarifying", "?"],
        "identifies_workflow": ["workflow", "step", "handoff"],
        "defines_success_metrics": ["success metrics", "measurement", "baseline"],
        "includes_risks": ["risk", "mitigation"],
        "discovery_discipline": [
            "discovery questions",
            "workflow",
            "stakeholder",
            "success metrics",
            "risk",
            "evaluation plan",
        ],
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
