"""Integration seam for sending lab artifacts to the EDD platform."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from edd_agent_lab.integrations.publish import PUBLISH_SCHEMA_VERSION, build_publish_envelope
from edd_agent_lab.paths import LAB_RUNS_DIR

PUBLISH_QUEUE_DIR = LAB_RUNS_DIR / "_platform_publish_queue"
RUN_INGEST_PATH = "/v1/integrations/runs/publish"
LAB_PUBLISH_PATH = "/v1/integrations/lab/publish"  # deprecated alias


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

    def publish_envelope(self, envelope: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("EDD platform integration is not wired yet.")

    def publish_run_record(self, run_record: dict[str, Any]) -> dict[str, Any]:
        return self.publish_envelope(build_publish_envelope(run_record))

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
        self._published: dict[str, dict[str, Any]] = {}

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

    def publish_envelope(self, envelope: dict[str, Any]) -> dict[str, Any]:
        run_id = str(envelope["run_id"])
        self._published[run_id] = envelope
        platform_run_id = f"local-published-{run_id}"
        self._runs[platform_run_id] = {
            "agent": envelope["agent"],
            "agent_version": envelope["agent_version"],
            "suite": envelope["suite"],
            "scenario_ids": envelope.get("scenario_ids", []),
            "agent_outputs": envelope.get("outputs", {}),
            "eval_summary": envelope.get("eval_summary"),
            "failure_packet": envelope.get("failure_packet"),
        }
        return {
            "status": "published_local",
            "platform_run_id": platform_run_id,
            "schema_version": PUBLISH_SCHEMA_VERSION,
        }


class QueuedEDDClient(LocalEDDClient):
    """Writes publish envelopes to disk for later platform ingestion."""

    def __init__(self, queue_dir: Path | None = None) -> None:
        super().__init__()
        self.queue_dir = queue_dir or PUBLISH_QUEUE_DIR
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def publish_envelope(self, envelope: dict[str, Any]) -> dict[str, Any]:
        result = super().publish_envelope(envelope)
        run_id = str(envelope["run_id"]).replace("/", "-")
        path = self.queue_dir / f"{run_id}.json"
        path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        result["status"] = "queued"
        result["queue_path"] = str(path)
        return result


class HttpEDDClient(EDDClient):
    """HTTP publisher for the EDD platform run ingest endpoint."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        tenant_id: str | None = None,
        timeout_seconds: float = 30.0,
        fallback_client: QueuedEDDClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.timeout_seconds = timeout_seconds
        self.fallback_client = fallback_client or QueuedEDDClient()
        self._runs: dict[str, dict[str, Any]] = {}

    def create_experiment_run(
        self, agent: str, agent_version: str, suite: str, scenario_ids: list[str]
    ) -> str:
        run_id = f"http-{agent}-{agent_version}-{suite}-{uuid4().hex[:8]}"
        self._runs[run_id] = {
            "agent": agent,
            "agent_version": agent_version,
            "suite": suite,
            "scenario_ids": scenario_ids,
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
            self._runs[run_id].setdefault("agent_outputs", {})[scenario_id] = {
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
        before_summary = self._summary_for_run_id(before_run_id)
        after_summary = self._summary_for_run_id(after_run_id)
        if before_summary is None or after_summary is None:
            return self.fallback_client.compare_runs(before_run_id, after_run_id)
        before_score = float(before_summary.get("overall_score", 0.0))
        after_score = float(after_summary.get("overall_score", 0.0))
        return {
            "before_run_id": before_run_id,
            "after_run_id": after_run_id,
            "before_summary": before_summary,
            "after_summary": after_summary,
            "delta_overall_score": round(after_score - before_score, 3),
            "status": "http_summary",
        }

    def publish_envelope(self, envelope: dict[str, Any]) -> dict[str, Any]:
        payload = dict(envelope)
        if self.tenant_id:
            payload["tenant_id"] = self.tenant_id
        try:
            response = self._request("POST", RUN_INGEST_PATH, json=payload)
        except Exception as exc:
            queued = self.fallback_client.publish_envelope(envelope)
            queued["status"] = "queued_after_http_error"
            queued["error"] = str(exc)
            return queued

        platform_run_id = response.get("platform_run_id") or response.get("experiment_run_id")
        if platform_run_id:
            self._runs[str(platform_run_id)] = {
                "eval_summary": envelope.get("eval_summary"),
                "failure_packet": envelope.get("failure_packet"),
            }
        return {
            "status": "published_http",
            "platform_run_id": platform_run_id,
            "gate_status": response.get("gate_status"),
            "gate_explanation": response.get("gate_explanation"),
            "schema_version": PUBLISH_SCHEMA_VERSION,
            "response": response,
        }

    def _summary_for_run_id(self, run_id: str) -> dict[str, Any] | None:
        cached = self._runs.get(run_id, {})
        summary = cached.get("eval_summary")
        if summary:
            return summary
        try:
            return self._request("GET", f"/v1/experiment-runs/{run_id}/summary")
        except Exception:
            return None

    def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        import httpx

        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.request(method, url, json=json, headers=headers)
            response.raise_for_status()
            if not response.content:
                return {}
            data = response.json()
            if isinstance(data, dict):
                return data
            return {"data": data}


def get_edd_client() -> EDDClient:
    mode = os.environ.get("EDD_CLIENT_MODE", "auto").strip().lower()
    base_url = os.environ.get("EDD_API_BASE_URL", "").strip()
    if mode == "local" or (mode == "auto" and not base_url):
        return LocalEDDClient()
    if mode in {"http", "auto"} and base_url:
        return HttpEDDClient(
            base_url=base_url,
            api_key=os.environ.get("EDD_API_KEY"),
            tenant_id=os.environ.get("EDD_TENANT_ID"),
        )
    raise ValueError(f"Unsupported EDD_CLIENT_MODE: {mode}")


def publish_run_record_file(path: Path, client: EDDClient | None = None) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    publisher = client or get_edd_client()
    return publisher.publish_run_record(record)
