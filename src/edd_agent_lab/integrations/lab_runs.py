"""Paths and helpers for versioned lab run artifacts."""

from __future__ import annotations

from pathlib import Path

from edd_agent_lab.paths import LAB_RUNS_DIR

AGENT_DIR_NAMES = {
    "customer-solution": "customer_solution_agent",
    "customer_solution": "customer_solution_agent",
    "customer_solution_agent": "customer_solution_agent",
    "customer-escalation-triage": "customer_escalation_triage",
    "customer_escalation_triage": "customer_escalation_triage",
}


def agent_run_dir(agent_key: str, version_dir: str) -> Path:
    dirname = AGENT_DIR_NAMES.get(agent_key, agent_key.replace("-", "_"))
    return LAB_RUNS_DIR / dirname / version_dir


def run_record_path(agent_key: str, version_dir: str) -> Path:
    return agent_run_dir(agent_key, version_dir) / "run-record.json"
