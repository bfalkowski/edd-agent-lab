"""Integration seam for sending lab artifacts to the EDD platform.

This repo stays local-first by default. The client below is intentionally thin and
platform-agnostic so internals can later swap to HTTP/MCP without changing lab logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class EDDClient:
    """Stable interface for publishing run/eval artifacts."""

    def create_experiment_run(
        self, agent: str, agent_version: str, suite: str, scenario_ids: list[str]
    ) -> str:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def log_agent_output(
        self,
        run_id: str,
        scenario_id: str,
        output: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def log_eval_summary(self, run_id: str, eval_summary: dict[str, Any]) -> None:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def log_failure_packet(self, run_id: str, failure_packet: dict[str, Any]) -> None:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def compare_runs(self, before_run_id: str, after_run_id: str) -> dict[str, Any]:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    # Compatibility shims for older method names used in early milestones.
    def create_run(self, agent: str, suite: str) -> str:
        return self.create_experiment_run(
            agent=agent,
            agent_version="unknown",
            suite=suite,
            scenario_ids=[],
        )

    def log_eval_result(self, run_id: str, result: dict[str, Any]) -> None:
        self.log_eval_summary(run_id=run_id, eval_summary=result)

    def create_failure_packet(self, run_id: str, packet: dict[str, Any]) -> None:
        self.log_failure_packet(run_id=run_id, failure_packet=packet)


class LocalEDDClient(EDDClient):
    """Local in-memory/no-op implementation used by default."""

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    def create_experiment_run(
        self, agent: str, agent_version: str, suite: str, scenario_ids: list[str]
    ) -> str:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        run_id = f"local-{agent}-{agent_version}-{suite}-{timestamp}"
        self._runs[run_id] = {
            "agent": agent,
            "agent_version": agent_version,
            "suite": suite,
            "scenario_ids": scenario_ids,
            "agent_outputs": {},
            "eval_summary": None,
            "failure_packet": None,
        }
        return run_id

    def log_agent_output(
        self,
        run_id: str,
        scenario_id: str,
        output: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if run_id in self._runs:
            self._runs[run_id]["agent_outputs"][scenario_id] = {
                "output": output,
                "metadata": metadata or {},
            }

    def log_eval_summary(self, run_id: str, eval_summary: dict[str, Any]) -> None:
        if run_id in self._runs:
            self._runs[run_id]["eval_summary"] = eval_summary

    def log_failure_packet(self, run_id: str, failure_packet: dict[str, Any]) -> None:
        if run_id in self._runs:
            self._runs[run_id]["failure_packet"] = failure_packet

    def compare_runs(self, before_run_id: str, after_run_id: str) -> dict[str, Any]:
        before = self._runs.get(before_run_id, {})
        after = self._runs.get(after_run_id, {})
        return {
            "before_run_id": before_run_id,
            "after_run_id": after_run_id,
            "before_summary": before.get("eval_summary"),
            "after_summary": after.get("eval_summary"),
            "status": "local_stub",
        }
