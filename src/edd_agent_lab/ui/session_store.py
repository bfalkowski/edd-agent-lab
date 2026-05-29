"""Persist and restore side-by-side console sessions on disk."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from typing import Literal

from pydantic import BaseModel, Field

from edd_agent_lab.evals.turn_schemas import TurnComparison, TurnEvaluation, TurnSummary
from edd_agent_lab.paths import LAB_RUNS_DIR

ConsoleGenerationMode = Literal["mock", "live"]

CONSOLE_SESSIONS_DIR = LAB_RUNS_DIR / "customer_solution_agent" / "console-sessions"


class ChatTurn(BaseModel):
    user: str
    left_response: str
    right_response: str
    turn_id: str | None = None


class ConsoleSession(BaseModel):
    session_id: str
    created_at: str
    updated_at: str
    scenario_id: str
    suite_id: str
    left_version: str
    right_version: str
    generation_mode: ConsoleGenerationMode = "mock"
    chat_turns: list[ChatTurn] = Field(default_factory=list)
    turn_summaries: list[TurnSummary] = Field(default_factory=list)
    latest_artifact_dir: str | None = None


def session_path(session_id: str) -> Path:
    return CONSOLE_SESSIONS_DIR / session_id / "session.json"


def save_console_session(session: ConsoleSession) -> Path:
    path = session_path(session.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    session.updated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_console_session(session_id: str) -> ConsoleSession | None:
    path = session_path(session_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return _normalize_session(data)


def list_console_session_ids(*, limit: int = 20) -> list[str]:
    if not CONSOLE_SESSIONS_DIR.is_dir():
        return []
    sessions: list[tuple[float, str]] = []
    for entry in CONSOLE_SESSIONS_DIR.iterdir():
        if not entry.is_dir():
            continue
        session_file = entry / "session.json"
        if not session_file.is_file():
            continue
        sessions.append((session_file.stat().st_mtime, entry.name))
    sessions.sort(reverse=True)
    return [session_id for _, session_id in sessions[:limit]]


def load_turn_eval(
    session_id: str,
    turn_id: str,
) -> tuple[TurnEvaluation | None, TurnComparison | None]:
    turn_dir = CONSOLE_SESSIONS_DIR / session_id / "turns" / turn_id
    eval_path = turn_dir / "turn-evaluation.json"
    comparison_path = turn_dir / "turn-comparison.json"
    if not eval_path.is_file() or not comparison_path.is_file():
        return None, None
    evaluation = TurnEvaluation.model_validate(json.loads(eval_path.read_text(encoding="utf-8")))
    comparison = TurnComparison.model_validate(
        json.loads(comparison_path.read_text(encoding="utf-8")),
    )
    return evaluation, comparison


def load_latest_turn_eval(session_id: str) -> tuple[TurnEvaluation | None, TurnComparison | None]:
    session = load_console_session(session_id)
    if not session or not session.turn_summaries:
        return None, None
    return load_turn_eval(session_id, session.turn_summaries[-1].turn_id)


def _normalize_session(data: dict[str, Any]) -> ConsoleSession:
    """Support legacy session.json files that only stored turn summaries."""
    if "chat_turns" not in data:
        data["chat_turns"] = []
    if "created_at" not in data:
        data["created_at"] = data.get("updated_at") or datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    if "updated_at" not in data:
        data["updated_at"] = data["created_at"]
    for key in ("scenario_id", "suite_id", "left_version", "right_version"):
        if key not in data:
            data[key] = _default_session_field(key)
    if "turn_summaries" not in data and "turns" in data:
        data["turn_summaries"] = data.pop("turns")
    if "generation_mode" not in data:
        data["generation_mode"] = "mock"
    return ConsoleSession.model_validate(data)


def _default_session_field(key: str) -> str:
    defaults = {
        "scenario_id": "healthcare_documentation",
        "suite_id": "discovery_quality",
        "left_version": "v0-baseline",
        "right_version": "v1-discovery-graph",
    }
    return defaults[key]
