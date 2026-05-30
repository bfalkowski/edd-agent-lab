"""Conversational response formatting for the side-by-side console."""

from __future__ import annotations

from edd_agent_lab.evals.schemas import Scenario

from .state import CustomerSolutionState

ChatMessage = dict[str, str]


def user_turn_count(conversation_history: list[ChatMessage] | None) -> int:
    if not conversation_history:
        return 0
    return sum(1 for item in conversation_history if item.get("role") == "user")


def _snippet(text: str, limit: int = 180) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _topic_hints(user_message: str) -> list[str]:
    lowered = user_message.lower()
    hints: list[str] = []
    mapping = {
        "metrics": ("metric", "measure", "kpi", "baseline", "success"),
        "workflow": ("workflow", "process", "step", "handoff", "intake"),
        "stakeholders": ("stakeholder", "clinician", "team", "owner", "partner"),
        "risks": ("risk", "compliance", "governance", "security", "liability"),
        "pilot": ("pilot", "rollout", "timeline", "phase"),
        "evaluation": ("eval", "test", "verify", "validation", "experiment"),
    }
    for topic, keywords in mapping.items():
        if any(word in lowered for word in keywords):
            hints.append(topic)
    return hints


def _questions_block(state: CustomerSolutionState, limit: int = 3) -> str:
    lines = []
    for item in state.discovery_questions[:limit]:
        lines.append(f"- {item.question}")
    return "\n".join(lines)


def _metrics_block(state: CustomerSolutionState) -> str:
    if not state.success_metrics:
        return "We should define baseline metrics before committing to a build."
    lines = []
    for item in state.success_metrics[:3]:
        lines.append(f"- **{item.metric}** — {item.how_to_measure}")
    return "\n".join(lines)


def _risks_block(state: CustomerSolutionState) -> str:
    if not state.risks:
        return "No material risks captured yet."
    lines = []
    for item in state.risks[:3]:
        lines.append(f"- {item.risk} Mitigation: {item.mitigation}")
    return "\n".join(lines)


def _first_turn_response(
    state: CustomerSolutionState,
    scenario: Scenario,
    user_message: str,
    agent_version: str,
) -> str:
    quote = _snippet(user_message)
    if agent_version == "v0-baseline":
        return (
            f"Thanks — I read your note about **{quote}**.\n\n"
            f"For **{scenario.title}**, I'd start with a focused {scenario.domain} copilot on "
            f"one workflow segment rather than a broad rollout.\n\n"
            f"**Proposed direction:** {state.proposed_solution or 'TBD'}\n\n"
            "To move fast, I'd track cycle time, quality/safety, and adoption in a 4–6 week pilot."
        )

    if agent_version == "v3-competency-model":
        competency_note = ""
        if state.discovery_competencies:
            competency_note = (
                "\n\nI'll work through our discovery competency checklist "
                f"({', '.join(state.discovery_competencies[:3])}, …) before solution design."
            )
        return (
            f"Thanks for the context on **{quote}**.\n\n"
            "Before solutioning, I want to validate a few discovery dimensions:\n\n"
            f"{_questions_block(state)}\n\n"
            f"Once we align on workflow scope and stakeholders for this {scenario.domain} "
            f"case, I'll propose metrics, risks, and a pilot plan."
            f"{competency_note}"
        )

    return (
        f"Thanks — you mentioned **{quote}**.\n\n"
        "I'm not ready to commit to a solution yet. A few clarifying questions first:\n\n"
        f"{_questions_block(state)}\n\n"
        f"After we narrow the pilot workflow in {scenario.domain}, I'll outline stakeholders, "
        "success metrics, risks, and an evaluation plan."
    )


def _followup_v0(
    state: CustomerSolutionState,
    scenario: Scenario,
    quote: str,
    topics: list[str],
) -> str:
    parts = [
        f"Got it — on **{quote}**, here's a pragmatic {scenario.domain} take:\n"
    ]
    if "metrics" in topics or not topics:
        parts.append(f"**Pilot metrics (week 1 baseline)**\n{_metrics_block(state)}\n")
        parts.append(
            "I'd instrument these in the first pilot cohort and review weekly "
            "before expanding scope.\n"
        )
    if "workflow" in topics:
        parts.append(
            f"**Workflow focus**\n"
            f"{state.workflow_summary or 'Target the highest-burden documentation step first.'}\n"
        )
    if "stakeholders" in topics:
        stakeholders = ", ".join(state.stakeholders[:6]) if state.stakeholders else "TBD"
        parts.append(f"**Owners for the pilot:** {stakeholders}\n")
    if "risks" in topics:
        parts.append(f"**Risks to watch**\n{_risks_block(state)}\n")
    if "pilot" in topics:
        parts.append(f"**Pilot plan**\n{state.pilot_plan or '4–6 week pilot on one unit.'}\n")
    if "evaluation" in topics:
        eval_plan = state.eval_plan or "Compare pilot vs. baseline cohort."
        parts.append(f"**How we'll verify**\n{eval_plan}\n")
    solution = state.proposed_solution or "Copilot on highest-burden workflow step."
    parts.append(f"**Solution angle:** {solution}")
    return "\n".join(parts)


def _followup_v1(
    state: CustomerSolutionState,
    scenario: Scenario,
    quote: str,
    topics: list[str],
) -> str:
    parts = [
        f"On **{quote}** — I want to answer without skipping discovery in this "
        f"{scenario.domain} case:\n"
    ]
    if "metrics" in topics or not topics:
        parts.append(
            "**Metrics I'd propose (pending workflow confirmation)**\n"
            f"{_metrics_block(state)}\n"
        )
        parts.append(
            "These only hold once we agree on the pilot workflow segment and "
            "who owns measurement.\n"
        )
    if "workflow" in topics:
        parts.append(
            f"**Workflow (still validating)**\n"
            f"{state.workflow_summary or 'Workflow mapping is still in progress.'}\n"
        )
    if "stakeholders" in topics:
        stakeholders = ", ".join(state.stakeholders[:6]) if state.stakeholders else "TBD"
        parts.append(f"**Stakeholders to involve:** {stakeholders}\n")
    if "risks" in topics:
        parts.append(f"**Risks**\n{_risks_block(state)}\n")
    if "pilot" in topics:
        parts.append(f"**Pilot plan**\n{state.pilot_plan or 'Pilot scope not finalized yet.'}\n")
    if "evaluation" in topics:
        parts.append(f"**Evaluation plan**\n{state.eval_plan or 'Eval plan pending.'}\n")
    if state.discovery_questions:
        parts.append("**Still need clarity on:**\n" + _questions_block(state, limit=2))
    return "\n".join(parts)


def _followup_v3(
    state: CustomerSolutionState,
    scenario: Scenario,
    quote: str,
    topics: list[str],
) -> str:
    if state.discovery_competencies:
        competencies = ", ".join(state.discovery_competencies[:4])
    else:
        competencies = "scope, metrics, risks"
    parts = [
        f"On **{quote}** — mapping this to our discovery competencies "
        f"({competencies}):\n"
    ]
    if "metrics" in topics or not topics:
        parts.append(f"**Metrics competency**\n{_metrics_block(state)}\n")
    if "workflow" in topics:
        parts.append(
            f"**Workflow competency**\n"
            f"{state.workflow_summary or 'Workflow mapping is still in progress.'}\n"
        )
    if "stakeholders" in topics:
        stakeholders = ", ".join(state.stakeholders[:6]) if state.stakeholders else "TBD"
        parts.append(f"**Stakeholder competency:** {stakeholders}\n")
    if "risks" in topics:
        parts.append(f"**Risk competency**\n{_risks_block(state)}\n")
    if "pilot" in topics:
        pilot_plan = state.pilot_plan or "Pilot scope not finalized yet."
        parts.append(f"**Pilot competency**\n{pilot_plan}\n")
    if "evaluation" in topics:
        parts.append(f"**Evaluation competency**\n{state.eval_plan or 'Eval plan pending.'}\n")
    if state.discovery_questions:
        parts.append("**Open competency gaps:**\n" + _questions_block(state, limit=2))
    return "\n".join(parts)


def _followup_response(
    state: CustomerSolutionState,
    scenario: Scenario,
    user_message: str,
    agent_version: str,
) -> str:
    quote = _snippet(user_message)
    topics = _topic_hints(user_message)
    if agent_version == "v0-baseline":
        return _followup_v0(state, scenario, quote, topics)
    if agent_version == "v3-competency-model":
        return _followup_v3(state, scenario, quote, topics)
    return _followup_v1(state, scenario, quote, topics)


def format_chat_response(
    state: CustomerSolutionState,
    scenario: Scenario,
    *,
    user_message: str,
    conversation_history: list[ChatMessage] | None,
    agent_version: str,
) -> str:
    """Turn graph state into a conversational reply for the console."""
    turn = user_turn_count(conversation_history) + 1
    if turn <= 1:
        return _first_turn_response(state, scenario, user_message, agent_version)
    return _followup_response(state, scenario, user_message, agent_version)


def is_brief_response(text: str) -> bool:
    return text.lstrip().startswith("# Customer Solution Discovery Brief")
