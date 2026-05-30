"""Mock reference runner for Customer Escalation Triage (HLD-005)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from edd_agent_lab.agents.registry import normalize_agent_dir
from edd_agent_lab.paths import LAB_RUNS_DIR, REPO_ROOT
from edd_agent_lab.scenarios.loading import load_scenario

MOCK_DATA_DIR = REPO_ROOT / "data" / "mock" / "customer_escalation_triage" / "apex_health"


@dataclass
class EscalationRunResult:
    run_id: str
    agent: str
    agent_version: str
    scenario_id: str
    output_path: Path
    final_response: str
    generation_mode: Literal["mock"] = "mock"


def _load_mock_bundle() -> dict[str, object]:
    bundle: dict[str, object] = {}
    for name in (
        "customer_report",
        "langfuse_trace_summary",
        "eval_results",
        "recent_changes",
        "tool_health",
        "customer_context",
    ):
        path = MOCK_DATA_DIR / f"{name}.json"
        bundle[name] = json.loads(path.read_text(encoding="utf-8"))
    return bundle


def _render_v0_response(bundle: dict[str, object]) -> str:
    report = bundle["customer_report"]
    assert isinstance(report, dict)
    customer = report.get("customer", "Apex Health")
    return (
        "## Triage summary\n"
        f"Customer {customer} reported inconsistent answers and latency.\n\n"
        "## Root cause\n"
        "The summarization prompt change two days ago is the likely cause of the regression.\n\n"
        "## Recommendation\n"
        "Tell the customer the issue has been found and the prompt will be rolled back."
    )


def _render_v1_response(bundle: dict[str, object]) -> str:
    report = bundle["customer_report"]
    trace = bundle["langfuse_trace_summary"]
    assert isinstance(report, dict)
    assert isinstance(trace, dict)
    return (
        "## Facts\n"
        f"- {report.get('reported_issue', '').strip()}\n"
        f"- {report.get('reported_latency', '').strip()}\n"
        "- A summarization prompt changed two days ago.\n"
        "- Eval scores dropped for scanned PDF cases.\n\n"
        "## Hypotheses\n"
        "- Prompt change may contribute to quality regression.\n"
        "- Tool timeouts may contribute to latency.\n\n"
        "## Unknowns\n"
        "- Whether prompt change alone explains the full regression.\n\n"
        "## Immediate actions\n"
        "- Pause further prompt changes.\n"
        "- Inspect eligibility-check timeouts and scanned PDF eval cases.\n\n"
        "## Customer update\n"
        "We are investigating inconsistent answers and latency. We have not confirmed a root cause."
    )


def run_customer_escalation_triage(
    *,
    scenario_id: str,
    agent_key: str = "customer-escalation-triage",
    agent_version: str = "v0-baseline",
    generation_mode: str | None = None,
) -> EscalationRunResult:
    _ = generation_mode
    _ = load_scenario(agent_key, scenario_id)
    bundle = _load_mock_bundle()
    if agent_version == "v0-baseline":
        final_response = _render_v0_response(bundle)
    elif agent_version == "v1-evidence-triage-graph":
        final_response = _render_v1_response(bundle)
    else:
        msg = f"Unsupported escalation agent version: {agent_version}"
        raise ValueError(msg)

    run_id = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    agent_dir = normalize_agent_dir(agent_key)
    out_dir = LAB_RUNS_DIR / agent_dir / agent_version
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"run-{run_id}-{scenario_id}.json"
    payload = {
        "run_id": run_id,
        "agent": agent_dir,
        "agent_version": agent_version,
        "scenario_id": scenario_id,
        "generation_mode": "mock",
        "final_response": final_response,
        "mock_data_dir": str(MOCK_DATA_DIR),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return EscalationRunResult(
        run_id=run_id,
        agent=agent_dir,
        agent_version=agent_version,
        scenario_id=scenario_id,
        output_path=output_path,
        final_response=final_response,
    )
