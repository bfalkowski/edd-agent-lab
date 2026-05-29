"""MCP client seam for EDD platform tools (Milestone 8)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from edd_agent_lab.integrations.edd_client import get_edd_client, publish_run_record_file
from edd_agent_lab.paths import LAB_RUNS_DIR


class EddMcpClient:
    """Thin wrapper over lab + platform capabilities exposed as MCP-style tools."""

    def __init__(self, *, server_url: str | None = None) -> None:
        self.server_url = (server_url or os.environ.get("EDD_MCP_SERVER_URL", "")).strip()
        self._edd_client = get_edd_client()

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": "edd.run_eval_suite", "description": "Run a lab eval suite locally."},
            {"name": "edd.publish_run", "description": "Publish a lab run record envelope."},
            {"name": "edd.compare_runs", "description": "Compare two platform or local run ids."},
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "edd.run_eval_suite":
            return self._run_eval_suite(arguments)
        if name == "edd.publish_run":
            return self._publish_run(arguments)
        if name == "edd.compare_runs":
            return self._compare_runs(arguments)
        raise ValueError(f"Unsupported MCP tool: {name}")

    def _run_eval_suite(self, arguments: dict[str, Any]) -> dict[str, Any]:
        from edd_agent_lab.evals.runner import run_eval_suite

        result = run_eval_suite(
            agent_key=str(arguments.get("agent", "customer-solution")),
            suite_id=str(arguments["suite"]),
            agent_version=str(arguments.get("agent_version", "v0-baseline")),
        )
        return {
            "run_id": result.run_id,
            "summary_path": str(result.summary_path),
            "overall_score": result.summary.get("overall_score"),
        }

    def _publish_run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        run_record = Path(str(arguments["run_record"]))
        return publish_run_record_file(run_record, client=self._edd_client)

    def _compare_runs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._edd_client.compare_runs(
            before_run_id=str(arguments["before_run_id"]),
            after_run_id=str(arguments["after_run_id"]),
        )

    def invoke_remote(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.server_url:
            return self.call_tool(name, arguments)
        import httpx

        payload = {"name": name, "arguments": arguments}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self.server_url.rstrip('/')}/tools/invoke", json=payload)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"result": data}


def default_run_record_path(agent_version: str) -> Path:
    return (
        LAB_RUNS_DIR / "customer_solution_agent" / agent_version / "run-record.json"
    )


def invoke_mcp_tool(name: str, arguments_json: str) -> dict[str, Any]:
    arguments = json.loads(arguments_json) if arguments_json else {}
    client = EddMcpClient()
    if client.server_url:
        return client.invoke_remote(name, arguments)
    return client.call_tool(name, arguments)
