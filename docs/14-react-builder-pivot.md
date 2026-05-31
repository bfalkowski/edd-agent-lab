# React Builder Pivot Plan

## Decision

Move the greenfield agent builder out of Streamlit and rebuild it as a React app.
Keep Python as the local artifact and workflow engine.

Streamlit can remain temporarily for the reference demo while the new builder takes
shape. Do not spend more design time making the Streamlit builder beautiful. The
new builder does not need to preserve the current Streamlit layout, CSS, or
navigation model.

## Product Direction

The builder should feel closer to ChatGPT than a dashboard:

- first screen starts with a focused agent-idea composer
- existing drafts are easy to resume
- workflow state is visible but not the main navigation model
- artifact details are readable and secondary
- raw YAML is available only as details
- actions are clear: create target, generate design, run, evaluate, improve, publish

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

The React app owns presentation and interaction.

The FastAPI layer owns request/response shapes and calls the existing draft
workflow functions.

The workspace store remains the source of local draft artifacts until platform
persistence is implemented.

## First Slice

- Add a small FastAPI app for draft builder endpoints.
- Add a React/Vite app skeleton.
- Build a clean first screen:
  - top app bar
  - centered agent idea composer
  - recent drafts list
- Build a draft workbench screen:
  - left rail: draft list and workflow status
  - main pane: active action and readable artifact summary
  - details drawer/section for YAML later

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

Open `http://localhost:5173`.

The API server runs on `http://127.0.0.1:8002`; it is not the product UI.

## Execution Plan

1. Make the React builder the default local authoring surface.
2. Replace the artifact list with readable review panels instead of dark YAML-like
   tables.
3. Add scenario editing and run/evaluation detail views.
4. Add streaming step activity for live generation:
   - each workflow action should emit status events before, during, and after
     LLM/tool work
   - the UI should show current task, token/status messages, written artifacts,
     and failures inline with the active step
   - deterministic mock mode can emit the same event shape without provider keys
5. Add artifact review/edit/delete controls:
   - review YAML or rendered summaries from each workflow step
   - save edited artifacts back to the local draft workspace
   - delete non-target artifacts so a step can be regenerated
6. Add publish preview and platform publish wiring through the existing lab
   integration client.
7. Remove or archive the Streamlit greenfield builder once the React workflow can
   create, run, evaluate, improve, compare, and publish a draft.

## Initial API Endpoints

- `GET /api/drafts`
- `POST /api/drafts`
- `GET /api/drafts/{agent_key}`
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

## Agent Semantics

The builder creates agent artifacts, but not every builder step is itself an
agent. A single LLM call that drafts YAML is generation. A step becomes agentic
when it carries state, uses tools, loops on evidence or eval feedback, or makes
bounded decisions. The UI should label these honestly: generation, run,
evaluation, comparison, and publish.

## Non-Goals For The Pivot Slice

- No platform/Postgres persistence yet.
- No production graph editor.
- No live LLM calls.
- No attempt to make the old Streamlit builder beautiful.
- No commitment to backward-compatible UI behavior.
