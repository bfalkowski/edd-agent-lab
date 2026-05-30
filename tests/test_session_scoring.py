from edd_agent_lab.evals.session_scoring import summarize_session_scores
from edd_agent_lab.evals.turn_schemas import TurnSummary


def test_summarize_session_scores_returns_none_for_empty() -> None:
    assert (
        summarize_session_scores(
            [],
            left_version="v0-baseline",
            right_version="v1-discovery-graph",
        )
        is None
    )


def test_summarize_session_scores_averages_and_counts_wins() -> None:
    summaries = [
        TurnSummary(
            turn_id="t1",
            user_input="hello",
            artifact_dir="/tmp/t1",
            before_score=0.4,
            after_score=0.8,
            score_delta=0.4,
            decision="after version is better for this turn",
        ),
        TurnSummary(
            turn_id="t2",
            user_input="metrics?",
            artifact_dir="/tmp/t2",
            before_score=0.6,
            after_score=0.7,
            score_delta=0.1,
            decision="mixed result",
        ),
        TurnSummary(
            turn_id="t3",
            user_input="risks?",
            artifact_dir="/tmp/t3",
            before_score=0.5,
            after_score=0.5,
            score_delta=0.0,
            decision="no meaningful difference",
        ),
    ]
    result = summarize_session_scores(
        summaries,
        left_version="v0-baseline",
        right_version="v1-discovery-graph",
    )
    assert result is not None
    assert result.turn_count == 3
    assert result.left_avg_score == 0.5
    assert result.right_avg_score == round((0.8 + 0.7 + 0.5) / 3, 3)
    assert result.avg_delta == round((0.4 + 0.1 + 0.0) / 3, 3)
    assert result.right_turns_won == 2
    assert result.left_turns_won == 0
    assert result.tie_turns == 1
    assert len(result.per_turn) == 3


def test_summarize_session_scores_detects_right_session_win() -> None:
    summaries = [
        TurnSummary(
            turn_id="t1",
            user_input="a",
            artifact_dir="/tmp/t1",
            before_score=0.3,
            after_score=0.9,
            score_delta=0.6,
            decision="after version is better for this turn",
        ),
        TurnSummary(
            turn_id="t2",
            user_input="b",
            artifact_dir="/tmp/t2",
            before_score=0.2,
            after_score=0.8,
            score_delta=0.6,
            decision="after version is better for this turn",
        ),
    ]
    result = summarize_session_scores(
        summaries,
        left_version="v0-baseline",
        right_version="v1-discovery-graph",
    )
    assert result is not None
    assert "v1-discovery-graph is better for this session" in result.session_decision
