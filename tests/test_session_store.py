import json

from edd_agent_lab.ui.session_store import (
    ChatTurn,
    ConsoleSession,
    load_console_session,
    save_console_session,
    session_path,
)


def test_save_and_load_console_session(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import session_store

    monkeypatch.setattr(session_store, "CONSOLE_SESSIONS_DIR", tmp_path)

    session = ConsoleSession(
        session_id="2026-05-29T12-00-00Z",
        created_at="2026-05-29T12-00-00Z",
        updated_at="2026-05-29T12-00-00Z",
        scenario_id="healthcare_documentation",
        suite_id="discovery_quality",
        left_version="v0-baseline",
        right_version="v1-discovery-graph",
        chat_turns=[
            ChatTurn(
                user="Reduce documentation burden.",
                left_response="v0 reply",
                right_response="v1 reply",
                turn_id="2026-05-29T12-01-00Z-turn",
            )
        ],
    )
    save_console_session(session)
    loaded = load_console_session("2026-05-29T12-00-00Z")
    assert loaded is not None
    assert loaded.scenario_id == "healthcare_documentation"
    assert len(loaded.chat_turns) == 1
    assert loaded.chat_turns[0].left_response == "v0 reply"


def test_load_legacy_session_json(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import session_store

    monkeypatch.setattr(session_store, "CONSOLE_SESSIONS_DIR", tmp_path)
    legacy = {
        "session_id": "legacy-session",
        "turns": [
            {
                "turn_id": "t1",
                "user_input": "hello",
                "artifact_dir": "/tmp/turn",
                "before_score": 0.4,
                "after_score": 0.8,
                "score_delta": 0.4,
                "decision": "after version is better for this turn",
            }
        ],
    }
    path = session_path("legacy-session")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(legacy), encoding="utf-8")

    loaded = load_console_session("legacy-session")
    assert loaded is not None
    assert loaded.scenario_id == "healthcare_documentation"
    assert len(loaded.turn_summaries) == 1
    assert loaded.turn_summaries[0].turn_id == "t1"
