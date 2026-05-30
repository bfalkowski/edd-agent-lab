"""Multi-turn discovery playbooks for the side-by-side console."""

from __future__ import annotations

DISCOVERY_PLAYBOOK: list[str] = [
    (
        "We need an AI assistant for clinical documentation. "
        "Clinicians spend too long on notes after visits."
    ),
    "What metrics should we track to know this is working?",
    "Walk me through the current workflow from patient visit to signed note.",
    "Who are the main stakeholders and what risks should we plan for?",
    "How would you pilot this and what eval plan would you use before rollout?",
]

PLAYBOOK_LABELS = {
    "discovery": DISCOVERY_PLAYBOOK,
}
