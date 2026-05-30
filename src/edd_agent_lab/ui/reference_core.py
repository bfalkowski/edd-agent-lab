"""Core reference workbench logic (no Streamlit imports)."""

from __future__ import annotations

import os
from typing import Any

from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.evals.scorecard import (
    SuiteRunSnapshot,
    SuiteScorecardRow,
    snapshot_from_eval_result,
)
from edd_agent_lab.integrations.edd_client import get_edd_client, publish_run_record_file
from edd_agent_lab.integrations.lab_runs import run_record_path

AGENT_KEY = "customer-escalation-triage"
SUITE_ID = "escalation_triage"
SCENARIO_ID = "escalation-latency-quality-regression-001"
V0 = "v0-baseline"
V1 = "v1-evidence-triage-graph"

PLATFORM_CONSOLE_PAGES = {
    "overview": "/Overview",
    "failure_packets": "/Failure_Packets",
    "fix_plans": "/Fix_Plans",
    "compare_versions": "/Compare_Versions",
    "runs": "/Runs",
}


def run_suite_for_version(agent_version: str) -> SuiteRunSnapshot:
    result = run_eval_suite(
        agent_key=AGENT_KEY,
        suite_id=SUITE_ID,
        agent_version=agent_version,
    )
    return snapshot_from_eval_result(result, SUITE_ID)


def publish_version_run(agent_version: str) -> dict[str, Any]:
    record_path = run_record_path(AGENT_KEY, agent_version)
    if not record_path.is_file():
        raise FileNotFoundError(f"Run record not found: {record_path}")
    return publish_run_record_file(record_path, client=get_edd_client())


def platform_api_base_url() -> str | None:
    base = os.environ.get("EDD_API_BASE_URL", "").strip()
    return base or None


def platform_console_url(page: str = "overview") -> str:
    base = os.environ.get("EDD_CONSOLE_BASE_URL", "http://127.0.0.1:8501").rstrip("/")
    suffix = PLATFORM_CONSOLE_PAGES.get(page, "")
    return f"{base}{suffix}"


def eval_spec_configured() -> bool:
    return bool(os.environ.get("EDD_EVAL_SPEC_ID", "").strip())


def snapshot_to_dict(snapshot: SuiteRunSnapshot) -> dict[str, Any]:
    return {
        "agent_version": snapshot.agent_version,
        "suite_id": snapshot.suite_id,
        "run_id": snapshot.run_id,
        "overall_score": snapshot.overall_score,
        "passed": snapshot.passed,
        "summary_path": snapshot.summary_path,
        "failure_packet_path": snapshot.failure_packet_path,
        "rows": [row.__dict__ for row in snapshot.rows],
        "summary": snapshot.summary,
    }


def snapshot_from_dict(data: dict[str, Any] | None) -> SuiteRunSnapshot | None:
    if not data:
        return None
    rows = [SuiteScorecardRow(**row) for row in data.get("rows", [])]
    return SuiteRunSnapshot(
        agent_version=str(data["agent_version"]),
        suite_id=str(data["suite_id"]),
        run_id=str(data["run_id"]),
        overall_score=float(data["overall_score"]),
        passed=bool(data["passed"]),
        summary_path=str(data["summary_path"]),
        failure_packet_path=data.get("failure_packet_path"),
        rows=rows,
        summary=data.get("summary", {}),
    )


def check_platform_health() -> dict[str, Any]:
    import httpx

    api_base = os.environ.get("EDD_API_BASE_URL", "").strip().rstrip("/")
    if not api_base:
        return {"configured": False, "reachable": False, "message": "EDD_API_BASE_URL not set"}
    try:
        response = httpx.get(f"{api_base}/v1/health", timeout=3.0)
    except httpx.HTTPError as exc:
        return {
            "configured": True,
            "reachable": False,
            "message": str(exc),
            "api_base": api_base,
        }
    if response.status_code != 200:
        return {
            "configured": True,
            "reachable": False,
            "message": f"HTTP {response.status_code}",
            "api_base": api_base,
        }
    return {
        "configured": True,
        "reachable": True,
        "message": response.json().get("status", "ok"),
        "api_base": api_base,
    }
