"""Reference scenario demo path shared by the workbench UI and demo script."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from edd_agent_lab.agents.customer_escalation_triage.runner import run_customer_escalation_triage
from edd_agent_lab.evals.scorecard import SuiteRunSnapshot
from edd_agent_lab.integrations.reference_publish import load_reference_publish_artifacts
from edd_agent_lab.ui.reference_core import (
    SCENARIO_ID,
    V0,
    V1,
    publish_version_run,
    run_suite_for_version,
    snapshot_to_dict,
)


@dataclass
class PublishOutcome:
    agent_version: str
    status: str | None = None
    platform_run_id: str | None = None
    gate_status: str | None = None
    gate_explanation: str | None = None
    error: str | None = None


@dataclass
class DemoPathResult:
    v0_response: str
    v1_response: str
    v0_snapshot: SuiteRunSnapshot
    v1_snapshot: SuiteRunSnapshot
    publishes: list[PublishOutcome] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    @property
    def v0_passed(self) -> bool:
        return self.v0_snapshot.passed

    @property
    def v1_passed(self) -> bool:
        return self.v1_snapshot.passed


def run_reference_demo_path(*, publish: bool = False) -> DemoPathResult:
    v0_run = run_customer_escalation_triage(scenario_id=SCENARIO_ID, agent_version=V0)
    v1_run = run_customer_escalation_triage(scenario_id=SCENARIO_ID, agent_version=V1)
    v0_snapshot = run_suite_for_version(V0)
    v1_snapshot = run_suite_for_version(V1)
    artifacts = load_reference_publish_artifacts()

    publishes: list[PublishOutcome] = []
    if publish:
        for version in (V0, V1):
            try:
                result = publish_version_run(version)
            except Exception as exc:
                publishes.append(PublishOutcome(agent_version=version, error=str(exc)))
                continue
            publishes.append(
                PublishOutcome(
                    agent_version=version,
                    status=str(result.get("status") or ""),
                    platform_run_id=(
                        str(result["platform_run_id"]) if result.get("platform_run_id") else None
                    ),
                    gate_status=str(result.get("gate_status") or "") or None,
                    gate_explanation=str(result.get("gate_explanation") or "") or None,
                )
            )

    return DemoPathResult(
        v0_response=v0_run.final_response,
        v1_response=v1_run.final_response,
        v0_snapshot=v0_snapshot,
        v1_snapshot=v1_snapshot,
        publishes=publishes,
        artifacts=artifacts,
    )


def demo_result_to_session(result: DemoPathResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "v0_response": result.v0_response,
        "v1_response": result.v1_response,
        "v0_snapshot": snapshot_to_dict(result.v0_snapshot),
        "v1_snapshot": snapshot_to_dict(result.v1_snapshot),
    }
    if result.publishes:
        payload["last_publish"] = _publish_to_dict(result.publishes[-1])
        payload["last_publish_batch"] = [_publish_to_dict(item) for item in result.publishes]
    return payload


def _publish_to_dict(outcome: PublishOutcome) -> dict[str, Any]:
    return {
        "agent_version": outcome.agent_version,
        "status": outcome.status,
        "platform_run_id": outcome.platform_run_id,
        "gate_status": outcome.gate_status,
        "gate_explanation": outcome.gate_explanation,
        "error": outcome.error,
    }


def format_demo_summary(result: DemoPathResult) -> str:
    lines = [
        "Customer Escalation Triage — reference demo path",
        f"v0 ({V0}): score {result.v0_snapshot.overall_score:.3f} · "
        f"{'pass' if result.v0_passed else 'fail'}",
        f"v1 ({V1}): score {result.v1_snapshot.overall_score:.3f} · "
        f"{'pass' if result.v1_passed else 'fail'}",
        f"Delta: {result.v1_snapshot.overall_score - result.v0_snapshot.overall_score:+.3f}",
    ]
    failure = result.artifacts.get("failure_packet") or {}
    if failure.get("id"):
        lines.append(f"v0 failure packet: {failure['id']} ({failure.get('failed_rule')})")
    gate = result.artifacts.get("gate_result") or {}
    if gate.get("overall_status"):
        lines.append(f"v1 gate: {gate['overall_status']}")
    for publish in result.publishes:
        if publish.error:
            lines.append(f"publish {publish.agent_version}: error — {publish.error}")
        else:
            lines.append(
                f"publish {publish.agent_version}: gate={publish.gate_status} "
                f"run={publish.platform_run_id or '-'}"
            )
    return "\n".join(lines)


def main() -> None:
    publish = os.environ.get("EDD_DEMO_PUBLISH", "").strip().lower() in {"1", "true", "yes"}
    result = run_reference_demo_path(publish=publish)
    print(format_demo_summary(result))


if __name__ == "__main__":
    main()
