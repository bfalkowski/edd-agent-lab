"""FastAPI routes for local draft agent building."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

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
    load_draft_artifacts,
    load_draft_target,
    run_draft_v0,
    run_draft_v1,
    save_design_scaffold,
    save_draft_artifact_source,
    save_draft_scenario,
    save_draft_target,
)


class CreateDraftRequest(BaseModel):
    name: str
    description: str


class ScenarioRequest(BaseModel):
    problem: str


class ArtifactSourceRequest(BaseModel):
    source: str


ACTION_HANDLERS = {
    "design": save_design_scaffold,
    "run-v0": run_draft_v0,
    "evaluate-v0": evaluate_draft_v0,
    "fix-plan": generate_draft_fix_plan,
    "v1-graph": generate_draft_v1_graph,
    "run-v1": run_draft_v1,
    "evaluate-v1": evaluate_draft_v1,
    "compare": compare_draft_versions,
}

ACTION_EVENTS = {
    "design": ("behavior_rules", "Generating design artifacts."),
    "run-v0": ("v0_run", "Running v0 candidate."),
    "evaluate-v0": ("eval_summary", "Evaluating v0 response."),
    "fix-plan": ("fix_plan", "Creating fix plan."),
    "v1-graph": ("graph_design_v1", "Generating v1 graph."),
    "run-v1": ("v1_run", "Running v1 candidate."),
    "evaluate-v1": ("eval_summary_v1", "Evaluating v1 response."),
    "compare": ("comparison", "Comparing v0 and v1."),
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
    def stream_action(agent_key: str, action: str):
        if action not in ACTION_HANDLERS:
            raise HTTPException(status_code=404, detail=f"Unknown action: {action}")

        def events():
            artifact_id, message = ACTION_EVENTS[action]
            yield _event(
                step_id=artifact_id,
                phase="starting",
                message=f"Starting {action}.",
                artifact_id=artifact_id,
            )
            yield _event(
                step_id=artifact_id,
                phase="running",
                message=message,
                artifact_id=artifact_id,
            )
            try:
                _run_action(agent_key, ACTION_HANDLERS[action])
                draft = load_draft(agent_key)
            except Exception as exc:
                yield _event(
                    step_id=artifact_id,
                    phase="failed",
                    message=str(exc),
                    artifact_id=artifact_id,
                )
                return
            yield _event(
                step_id=artifact_id,
                phase="completed",
                message=f"Wrote {artifact_id}.",
                artifact_id=artifact_id,
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
    def run_v0(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, run_draft_v0)
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
    def run_v1(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, run_draft_v1)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/evaluate-v1")
    def evaluate_v1(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, evaluate_draft_v1)
        return load_draft(agent_key)

    @app.post("/api/drafts/{agent_key}/compare")
    def compare_versions(agent_key: str) -> dict[str, Any]:
        _run_action(agent_key, compare_draft_versions)
        return load_draft(agent_key)

    return app


def _run_action(agent_key: str, action):
    try:
        return action(agent_key)
    except FileNotFoundError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _event(**payload: Any) -> str:
    return json.dumps(payload) + "\n"


app = create_app()
