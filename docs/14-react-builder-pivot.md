# React Builder Architecture

The local builder is a React app backed by a small FastAPI service.

Python owns the local EDD workflow and artifact store. React owns presentation,
interaction, review, and editing.

## Architecture

```text
React builder UI
        |
        | HTTP JSON
        v
FastAPI local API
        |
        v
workspace_store.py
        |
        v
lab-runs/<agent>/draft/*.yaml
```

## Local Run Commands

API:

```bash
uv run --extra web uvicorn edd_agent_lab.api.builder:app --host 127.0.0.1 --port 8002
```

React builder:

```bash
cd web/agent-builder
npm run dev
```

Open:

```text
http://localhost:5173
```

The API server runs on:

```text
http://127.0.0.1:8002
```

## Product Model

The builder starts from an agent idea and turns it into local EDD artifacts.

The primary UI model is:

```text
project list -> selected draft -> workflow steps -> step outputs -> artifact review
```

Each workflow step owns:

- status
- action
- transient activity
- generated outputs
- review/edit/delete controls for its artifacts

## API Endpoints

- `GET /`
- `GET /health`
- `GET /api/drafts`
- `POST /api/drafts`
- `GET /api/drafts/{agent_key}`
- `DELETE /api/drafts/{agent_key}`
- `POST /api/drafts/{agent_key}/design`
- `POST /api/drafts/{agent_key}/scenario`
- `POST /api/drafts/{agent_key}/run-v0`
- `POST /api/drafts/{agent_key}/evaluate-v0`
- `POST /api/drafts/{agent_key}/fix-plan`
- `POST /api/drafts/{agent_key}/v1-graph`
- `POST /api/drafts/{agent_key}/run-v1`
- `POST /api/drafts/{agent_key}/evaluate-v1`
- `POST /api/drafts/{agent_key}/compare`
- `PUT /api/drafts/{agent_key}/artifacts/{artifact_key}`
- `DELETE /api/drafts/{agent_key}/artifacts/{artifact_key}`

## Streaming Design

Workflow actions should eventually stream progress events.

Event shape should work in deterministic mode and live mode:

```json
{
  "step_id": "evaluate-v1",
  "phase": "running",
  "message": "Evaluating candidate response.",
  "artifact_id": "eval_summary_v1"
}
```

The UI should show those events inline on the owning step. Activity is
ephemeral; once the workflow advances to another step, the previous status text
can clear.

## Agent Semantics

The builder creates agent artifacts, but not every builder step is itself an
agent. A single model call that drafts YAML is generation. A step becomes
agentic when it carries state, uses tools, loops on evidence or eval feedback,
or makes bounded decisions.

Use honest labels:

- generate design
- run candidate
- evaluate
- compare
- publish
