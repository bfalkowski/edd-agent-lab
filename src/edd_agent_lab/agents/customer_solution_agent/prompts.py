"""Version-specific prompts for live agent generation."""

from __future__ import annotations

from edd_agent_lab.evals.schemas import Scenario

from .competency import DISCOVERY_COMPETENCIES

VERSION_POLICIES: dict[str, str] = {
    "v0-baseline": (
        "You are v0-baseline: a solution-first customer discovery agent. "
        "Move quickly toward a concrete copilot proposal. Ask at most one or two "
        "clarifying questions. Emphasize pilot metrics, risks, and a pragmatic rollout."
    ),
    "v1-discovery-graph": (
        "You are v1-discovery-graph: a discovery-first agent. "
        "Do NOT finalize a solution until discovery gaps are addressed. "
        "Ask multiple clarifying discovery questions. Decompose workflow, stakeholders, "
        "success metrics, risks, pilot plan, and evaluation plan before solutioning."
    ),
    "v3-competency-model": (
        "You are v3-competency-model: apply the domain-neutral discovery competency "
        "framework explicitly before proposing solutions. Reference competency gaps and "
        "tie questions to scenario themes."
    ),
}


def discovery_draft_system_prompt(agent_version: str) -> str:
    policy = VERSION_POLICIES.get(agent_version, VERSION_POLICIES["v1-discovery-graph"])
    competencies = "\n".join(f"- {item}" for item in DISCOVERY_COMPETENCIES)
    return (
        f"{policy}\n\n"
        "Produce structured discovery state grounded in the customer's problem. "
        "Use scenario-specific details — do not copy generic healthcare examples when "
        "the scenario domain differs.\n\n"
        "Required coverage in your structured output:\n"
        "- problem_summary\n"
        "- discovery_questions (each with question + reason)\n"
        "- workflow_summary\n"
        "- stakeholders\n"
        "- assumptions\n"
        "- proposed_solution (null for v1 until discovery is sufficient)\n"
        "- success_metrics (metric, why_it_matters, how_to_measure)\n"
        "- risks (risk, mitigation)\n"
        "- pilot_plan\n"
        "- eval_plan\n"
        "- discovery_competencies (v3 only; empty list for other versions)\n\n"
        f"Discovery competency framework:\n{competencies}\n"
    )


def discovery_draft_user_prompt(
    scenario: Scenario,
    user_problem: str,
    *,
    agent_version: str,
) -> str:
    themes = ", ".join(scenario.expected_themes) or "none listed"
    version_note = ""
    if agent_version == "v0-baseline":
        version_note = (
            "\nVersion note: include a concrete proposed_solution and keep "
            "discovery_questions minimal.\n"
        )
    elif agent_version == "v1-discovery-graph":
        version_note = (
            "\nVersion note: prioritize discovery_questions and workflow decomposition; "
            "proposed_solution may be high-level but must follow discovery sections.\n"
        )
    elif agent_version == "v3-competency-model":
        version_note = (
            "\nVersion note: populate discovery_competencies from the framework and "
            "reference scenario themes in questions and risks.\n"
        )
    return (
        f"Scenario ID: {scenario.id}\n"
        f"Title: {scenario.title}\n"
        f"Domain: {scenario.domain}\n"
        f"Expected themes: {themes}\n\n"
        f"Customer input:\n{user_problem}\n"
        f"{version_note}"
    )


def chat_response_system_prompt(agent_version: str) -> str:
    policy = VERSION_POLICIES.get(agent_version, VERSION_POLICIES["v1-discovery-graph"])
    return (
        f"{policy}\n\n"
        "Write a conversational reply for the side-by-side chat console.\n"
        "Rules:\n"
        "- Reply in markdown.\n"
        "- Ground every claim in the provided discovery state and customer message.\n"
        "- Do NOT emit the full 'Customer Solution Discovery Brief' template.\n"
        "- First turn: v0 proposes direction; v1/v3 ask clarifying questions.\n"
        "- Follow-up turns: answer the latest customer message directly.\n"
        "- Include natural language references to workflow, success metrics, risks, "
        "and evaluation plan when relevant.\n"
        "- Keep responses under 350 words unless the customer asks for detail.\n"
    )


def chat_response_user_prompt(
    scenario: Scenario,
    user_message: str,
    discovery_state_json: str,
    conversation_history: list[dict[str, str]] | None,
) -> str:
    history_block = ""
    if conversation_history:
        lines = []
        for item in conversation_history:
            role = item.get("role", "user")
            label = "Customer" if role == "user" else "Agent"
            lines.append(f"{label}: {item.get('content', '').strip()}")
        history_block = "Conversation so far:\n" + "\n".join(lines) + "\n\n"

    return (
        f"Scenario: {scenario.title} ({scenario.domain})\n\n"
        f"{history_block}"
        f"Latest customer message:\n{user_message.strip()}\n\n"
        f"Structured discovery state (JSON):\n{discovery_state_json}\n"
    )
