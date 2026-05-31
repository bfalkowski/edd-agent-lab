"""FastAPI routes for local draft agent building."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel

from edd_agent_lab.agents.generation import (
    agent_model_name,
    live_generation_available,
    resolve_generation_mode,
)
from edd_agent_lab.ui.workspace_store import (
    compare_draft_versions,
    delete_draft_artifact,
    delete_draft_workspace,
    draft_artifact_cards,
    draft_comparison_view,
    draft_workflow_status,
    evaluate_draft_v0,
    evaluate_draft_v1,
    generate_draft_fix_plan,
    generate_draft_v1_graph,
    list_draft_workspaces,
    load_draft_artifact_sources,
    load_draft_artifact_validations,
    load_draft_artifacts,
    load_draft_target,
    publish_draft_evidence,
    run_draft_v0,
    run_draft_v1,
    save_design_scaffold,
    save_draft_artifact_source,
    save_draft_scenario,
    save_draft_target,
    update_behavior_rules,
    update_draft_target,
)


class CreateDraftRequest(BaseModel):
    name: str
    description: str


class ScenarioRequest(BaseModel):
    problem: str


class ArtifactSourceRequest(BaseModel):
    source: str


class TargetUpdateRequest(BaseModel):
    name: str
    purpose: str
    risk_tolerance: str
    expected_output_format: str


class BehaviorRuleRequest(BaseModel):
    id: str
    severity: str
    description: str
    target_id: str | None = None
    status: str


class BehaviorRulesUpdateRequest(BaseModel):
    rules: list[BehaviorRuleRequest]


GenerationModeRequest = Literal["mock", "live", "auto"]


ACTION_HANDLERS = {
    "design": save_design_scaffold,
    "run-v0": run_draft_v0,
    "evaluate-v0": evaluate_draft_v0,
    "fix-plan": generate_draft_fix_plan,
    "v1-graph": generate_draft_v1_graph,
    "run-v1": run_draft_v1,
    "evaluate-v1": evaluate_draft_v1,
    "compare": compare_draft_versions,
    "publish": publish_draft_evidence,
}

ACTION_EVENTS = {
    "design": {
        "step_id": "behavior_rules",
        "message": "Generating design artifacts.",
        "outputs": [
            "behavior_rules",
            "eval_contract",
            "eval_suite",
            "information_requirements",
            "tool_requirements",
            "graph_design",
        ],
    },
    "run-v0": {
        "step_id": "v0_run",
        "message": "Running v0 candidate.",
        "outputs": ["v0_run"],
    },
    "evaluate-v0": {
        "step_id": "eval_summary",
        "message": "Evaluating v0 response.",
        "outputs": ["eval_summary", "failure_packet"],
    },
    "fix-plan": {
        "step_id": "fix_plan",
        "message": "Creating fix plan.",
        "outputs": ["fix_plan"],
    },
    "v1-graph": {
        "step_id": "graph_design_v1",
        "message": "Generating v1 graph.",
        "outputs": ["graph_design_v1"],
    },
    "run-v1": {
        "step_id": "v1_run",
        "message": "Running v1 candidate.",
        "outputs": ["v1_run"],
    },
    "evaluate-v1": {
        "step_id": "eval_summary_v1",
        "message": "Evaluating v1 response.",
        "outputs": ["eval_summary_v1"],
    },
    "compare": {
        "step_id": "comparison",
        "message": "Comparing v0 and v1.",
        "outputs": ["comparison"],
    },
    "publish": {
        "step_id": "publish_result",
        "message": "Publishing draft evidence.",
        "outputs": ["publish_result"],
    },
}


def create_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse

    app = FastAPI(title="EDD Agent Lab Builder API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "EDD Agent Lab Builder API",
            "status": "ok",
            "ui": "http://localhost:5173",
            "drafts": "/api/drafts",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/runtime")
    def runtime() -> dict[str, Any]:
        return {
            "generation": {
                "default_mode": "auto",
                "resolved_mode": resolve_generation_mode("auto"),
                "live_available": live_generation_available(),
                "model": agent_model_name(),
            }
        }

    @app.get("/api/drafts")
    def list_drafts() -> dict[str, Any]:
        return {
            "drafts": [
                {
                    "agent_key": workspace.agent_key,
                    "name": workspace.name,
                    "updated_at": workspace.updated_at,
                    "target_path": str(workspace.target_path),
                }
                for workspace in list_draft_workspaces()
            ]
        }

    @app.post("/api/drafts")
    def create_draft(request: CreateDraftRequest) -> dict[str, Any]:
        try:
            workspace = save_draft_target(
                name=request.name,
                description=request.description,
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return load_draft(workspace.agent_key)

    @app.get("/api/drafts/{agent_key}")
    def load_draft(agent_key: str) -> dict[str, Any]:
        target = load_draft_target(agent_key)
        if target is None:
            raise HTTPException(status_code=404, detail="Draft not found")
        return {
            "agent_key": agent_key,
            "target": target,
            "artifacts": load_draft_artifacts(agent_key),
            "artifact_sources": load_draft_artifact_sources(agent_key),
            "artifact_validations": load_draft_artifact_validations(agent_key),
            "status": draft_workflow_status(agent_key),
            "artifact_cards": draft_artifact_cards(agent_key),
            "comparison_view": draft_comparison_view(agent_key),
        }

    @app.delete("/api/drafts/{agent_key}")
    def delete_draft(agent_key: str) -> dict[str, Any]:
        try:
            delete_draft_workspace(agent_key)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return list_drafts()

    @app.put("/api/drafts/{agent_key}/target")
    def update_target(agent_key: str, request: TargetUpdateRequest) -> dict[str, Any]:
        try:
            update_draft_target(
                agent_key=agent_key,
                name=request.name,
                purpose=request.purpose,
                risk_tolerance=request.risk_tolerance,
                expected_output_format=request.expected_output_format,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return load_draft(agent_key)

    @app.put("/api/drafts/{agent_key}/rules")
    def update_rules(agent_key: str, request: BehaviorRulesUpdateRequest) -> dict[str, Any]:
        try:
            update_behavior_rules(
                agent_key=agent_key,
                rules=[rule.model_dump() for rule in request.rules],
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return load_draft(agent_key)

    @app.put("/api/drafts/{agent_key}/artifacts/{artifact_key}")
    def update_artifact(
        agent_key: str,
        artifact_key: str,
        request: ArtifactSourceRequest,
    ) -> dict[str, Any]:
        try:
            save_draft_artifact_source(
                agent_key=agent_key,
                artifact_key=artifact_key,
                source=request.source,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return load_draft(agent_key)

    @app.delete("/api/drafts/{agent_key}/artifacts/{artifact_key}")
    def delete_artifact(agent_key: str, artifact_key: str) -> dict[str, Any]:
        try:
            delete_draft_artifact(agent_key=agent_key, artifact_key=artifact_key)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/design")
    def scaffold_design(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, save_design_scaffold)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/actions/{action}/stream")
    def stream_action(
        agent_key: str,
        action: str,
        generation_mode: GenerationModeRequest | None = None,
    ):
        if action not in ACTION_HANDLERS:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action}")

        def events():
            metadata = ACTION_EVENTS[action]
            step_id = metadata["step_id"]
            yield _event(
                step_id=step_id,
                phase="starting",
                message=f"Starting {action}.",
                retry_action=action,
                retryable=True,
            )
            yield _event(
                step_id=step_id,
                phase="running",
                message=_action_message(action, metadata["message"], generation_mode),
                retry_action=action,
                retryable=True,
            )
            try:
                _run_action(
                    agent_key,
                    ACTION_HANDLERS[action],
                    generation_mode=generation_mode,
                )
                draft = load_draft(agent_key)
            except Exception as exc:
                yield _event(
                    step_id=step_id,
                    phase="failed",
                    message=str(exc),
                    retry_action=action,
                    retryable=True,
                )
                return
            for output_id in metadata["outputs"]:
                artifact = next(
                    (
                        card
                        for card in draft["artifact_cards"]
                        if card["id"] == output_id and card["status"] == "ready"
                    ),
                    None,
                )
                if artifact is None:
                    continue
                yield _event(
                    step_id=step_id,
                    phase="artifact",
                    message=f"Wrote {artifact['file']}.",
                    artifact_id=output_id,
                    file=artifact["file"],
                    retry_action=action,
                    retryable=True,
                )
            yield _event(
                step_id=step_id,
                phase="completed",
                message="Step complete.",
                retry_action=action,
                retryable=False,
                draft=draft,
            )

        return StreamingResponse(events(), media_type="application/x-ndjson")

    @app.post("/api/drafts/{agent_key}/scenario")
    def save_scenario(agent_key: str, request: ScenarioRequest) -> dict[str, Any]:
        try:
            save_draft_scenario(agent_key=agent_key, problem=request.problem)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/run-v0")
    def run_v0(
        agent_key: str,
        generation_mode: GenerationModeRequest | None = None,
    ) -> dict[str, Any]:
        _run_action(agent_key, run_draft_v0, generation_mode=generation_mode)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/evaluate-v0")
    def evaluate_v0(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, evaluate_draft_v0)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/fix-plan")
    def fix_plan(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, generate_draft_fix_plan)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/v1-graph")
    def v1_graph(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, generate_draft_v1_graph)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/run-v1")
    def run_v1(
        agent_key: str,
        generation_mode: GenerationModeRequest | None = None,
    ) -> dict[str, Any]:
        _run_action(agent_key, run_draft_v1, generation_mode=generation_mode)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/evaluate-v1")
    def evaluate_v1(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, evaluate_draft_v1)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/compare")
    def compare_versions(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, compare_draft_versions)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/publish")
    def publish_evidence(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, publish_draft_evidence)
        return load_draft(agent_key)

    return app


def _run_action(
    agent_key: str,
    action,
    *,
    generation_mode: GenerationModeRequest | None = None,
):
    try:
        if action in {run_draft_v0, run_draft_v1}:
            return action(agent_key, generation_mode=generation_mode)
        return action(agent_key)
    except FileNotFoundError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _action_message(
    action: str,
    message: str,
    generation_mode: GenerationModeRequest | None,
) -> str:
    if action not in {"run-v0", "run-v1"}:
        return message
    try:
        resolved_mode = resolve_generation_mode(generation_mode)
    except RuntimeError:
        resolved_mode = "unavailable"
    return f"{message} Generation mode: {resolved_mode}."


def _event(**payload: Any) -> str:
    return json.dumps(payload) + "\n"


app = create_app()
