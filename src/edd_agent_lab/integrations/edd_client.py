"""Thin client for the Eval Driven Design platform (local no-op until Milestone 7)."""

from typing import Any


class EDDClient:
    """Interface for logging runs and failure packets to the EDD platform."""

    def create_run(self, agent: str, suite: str) -> str:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def log_eval_result(self, run_id: str, result: dict[str, Any]) -> None:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def create_failure_packet(self, run_id: str, packet: dict[str, Any]) -> None:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def compare_runs(self, before_run_id: str, after_run_id: str) -> dict[str, Any]:
        raise NotImplementedError("EDD platform integration is not wired yet.")


class LocalEDDClient(EDDClient):
    """No-op client for local-only lab runs."""

    def create_run(self, agent: str, suite: str) -> str:
        return f"local-{agent}-{suite}"

    def log_eval_result(self, run_id: str, result: dict[str, Any]) -> None:
        _ = (run_id, result)

    def create_failure_packet(self, run_id: str, packet: dict[str, Any]) -> None:
        _ = (run_id, packet)

    def compare_runs(self, before_run_id: str, after_run_id: str) -> dict[str, Any]:
        return {"before": before_run_id, "after": after_run_id, "status": "local_stub"}
