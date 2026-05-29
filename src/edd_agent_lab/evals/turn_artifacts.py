"""Write turn-level console artifacts under lab-runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from edd_agent_lab.evals.turn_schemas import TurnComparison, TurnEvaluation, TurnSummary
from edd_agent_lab.ui.session_store import CONSOLE_SESSIONS_DIR, ConsoleSession, save_console_session


def new_session_id() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def new_turn_id() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ-turn")


def write_turn_artifacts(
    session_id: str,
    turn_id: str,
    evaluation: TurnEvaluation,
    comparison: TurnComparison,
    *,
    session: ConsoleSession | None = None,
) -> Path:
    turn_dir = CONSOLE_SESSIONS_DIR / session_id / "turns" / turn_id
    turn_dir.mkdir(parents=True, exist_ok=True)

    eval_path = turn_dir / "turn-evaluation.json"
    comparison_json_path = turn_dir / "turn-comparison.json"
    comparison_md_path = turn_dir / "turn-comparison.md"

    eval_path.write_text(
        json.dumps(evaluation.model_dump(), indent=2),
        encoding="utf-8",
    )
    comparison_json_path.write_text(
        json.dumps(comparison.model_dump(), indent=2),
        encoding="utf-8",
    )
    comparison_md_path.write_text(_comparison_markdown(comparison, evaluation), encoding="utf-8")

    if session is not None:
        session.turn_summaries.append(
            TurnSummary(
                turn_id=turn_id,
                user_input=evaluation.user_input,
                artifact_dir=str(turn_dir),
                before_score=comparison.before_score,
                after_score=comparison.after_score,
                score_delta=comparison.score_delta,
                decision=comparison.decision,
            )
        )
        session.latest_artifact_dir = str(turn_dir)
        save_console_session(session)

    return turn_dir


def _comparison_markdown(comparison: TurnComparison, evaluation: TurnEvaluation) -> str:
    return "\n".join(
        [
            f"# Turn Comparison: {comparison.before_version} vs {comparison.after_version}",
            "",
            f"- Decision: **{comparison.decision}**",
            f"- Score delta: {comparison.score_delta:+.3f}",
            f"- Before: {comparison.before_score:.3f}",
            f"- After: {comparison.after_score:.3f}",
            "",
            "## Explanation",
            comparison.explanation,
            "",
            "## Improved Checks",
            ", ".join(comparison.improved_checks) or "(none)",
            "",
            "## Regressed Checks",
            ", ".join(comparison.regressed_checks) or "(none)",
            "",
            "## User Input",
            evaluation.user_input,
            "",
        ]
    )
