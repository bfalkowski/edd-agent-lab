"""Aggregate turn-level scores into session-level summaries."""

from __future__ import annotations

from pydantic import BaseModel, Field

from edd_agent_lab.evals.turn_schemas import TurnSummary


class SessionTurnScore(BaseModel):
    turn_id: str
    user_input: str
    left_score: float
    right_score: float
    score_delta: float
    decision: str


class SessionScoreSummary(BaseModel):
    left_version: str
    right_version: str
    turn_count: int
    left_avg_score: float
    right_avg_score: float
    avg_delta: float
    left_turns_won: int
    right_turns_won: int
    tie_turns: int
    session_decision: str
    explanation: str
    per_turn: list[SessionTurnScore] = Field(default_factory=list)


def summarize_session_scores(
    turn_summaries: list[TurnSummary],
    *,
    left_version: str,
    right_version: str,
) -> SessionScoreSummary | None:
    if not turn_summaries:
        return None

    per_turn: list[SessionTurnScore] = []
    left_total = 0.0
    right_total = 0.0
    delta_total = 0.0
    left_won = 0
    right_won = 0
    ties = 0

    for item in turn_summaries:
        per_turn.append(
            SessionTurnScore(
                turn_id=item.turn_id,
                user_input=item.user_input,
                left_score=item.before_score,
                right_score=item.after_score,
                score_delta=item.score_delta,
                decision=item.decision,
            )
        )
        left_total += item.before_score
        right_total += item.after_score
        delta_total += item.score_delta
        if item.after_score > item.before_score:
            right_won += 1
        elif item.before_score > item.after_score:
            left_won += 1
        else:
            ties += 1

    count = len(turn_summaries)
    left_avg = round(left_total / count, 3)
    right_avg = round(right_total / count, 3)
    avg_delta = round(delta_total / count, 3)
    decision, explanation = _session_decision(
        left_version=left_version,
        right_version=right_version,
        left_avg=left_avg,
        right_avg=right_avg,
        avg_delta=avg_delta,
        right_turns_won=right_won,
        left_turns_won=left_won,
        turn_count=count,
    )

    return SessionScoreSummary(
        left_version=left_version,
        right_version=right_version,
        turn_count=count,
        left_avg_score=left_avg,
        right_avg_score=right_avg,
        avg_delta=avg_delta,
        left_turns_won=left_won,
        right_turns_won=right_won,
        tie_turns=ties,
        session_decision=decision,
        explanation=explanation,
        per_turn=per_turn,
    )


def _session_decision(
    *,
    left_version: str,
    right_version: str,
    left_avg: float,
    right_avg: float,
    avg_delta: float,
    right_turns_won: int,
    left_turns_won: int,
    turn_count: int,
) -> tuple[str, str]:
    if left_avg == 0.0 and right_avg == 0.0:
        return (
            "insufficient evidence",
            "Both versions averaged zero across session turns.",
        )

    win_ratio = right_turns_won / turn_count
    if avg_delta >= 0.15 and win_ratio >= 0.5:
        return (
            f"{right_version} is better for this session",
            (
                f"{right_version} averaged {right_avg:.3f} vs {left_avg:.3f} for "
                f"{left_version} (avg delta {avg_delta:+.3f}). "
                f"Won {right_turns_won}/{turn_count} turns."
            ),
        )
    if avg_delta <= -0.10:
        return (
            f"{right_version} regressed for this session",
            (
                f"{right_version} averaged {right_avg:.3f}, below {left_version} at "
                f"{left_avg:.3f} (avg delta {avg_delta:+.3f})."
            ),
        )
    if abs(avg_delta) < 0.05:
        return (
            "no meaningful session difference",
            (
                f"Average score delta {avg_delta:+.3f} is within the no-change band "
                f"across {turn_count} turns."
            ),
        )
    if left_turns_won > right_turns_won:
        return (
            f"{left_version} leads this session",
            (
                f"{left_version} won {left_turns_won}/{turn_count} turns despite "
                f"avg delta {avg_delta:+.3f}."
            ),
        )
    return (
        "mixed session result",
        (
            f"Average delta {avg_delta:+.3f} with split turn wins "
            f"(left={left_turns_won}, right={right_turns_won}, "
            f"ties={turn_count - left_turns_won - right_turns_won})."
        ),
    )
