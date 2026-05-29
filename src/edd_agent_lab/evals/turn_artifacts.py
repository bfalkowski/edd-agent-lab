"""Write turn-level console artifacts under lab-runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from edd_agent_lab.evals.turn_schemas import TurnComparison, TurnEvaluation
from edd_agent_lab.paths import LAB_RUNS_DIR

CONSOLE_SESSIONS_DIR = LAB_RUNS_DIR / "customer_solution_agent" / "console-sessions"


def new_session_id() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def new_turn_id() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ-turn")


def write_turn_artifacts(
    session_id: str,
    turn_id: str,
    evaluation: TurnEvaluation,
    comparison: TurnComparison,
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

    session_path = CONSOLE_SESSIONS_DIR / session_id / "session.json"
    session_data = _load_session(session_path)
    session_data.setdefault("turns", []).append(
        {
            "turn_id": turn_id,
            "user_input": evaluation.user_input,
            "artifact_dir": str(turn_dir),
            "before_score": comparison.before_score,
            "after_score": comparison.after_score,
            "score_delta": comparison.score_delta,
            "decision": comparison.decision,
        }
    )
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
    return turn_dir


def _load_session(path: Path) -> dict[str, object]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"session_id": path.parent.name, "turns": []}


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
