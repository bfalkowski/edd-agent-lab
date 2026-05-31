# Developer Experience Today

This document describes how an agent developer works with **edd-agent-lab** and
**eval-driven-design-platform** right now.

For integration boundaries, see [05-platform-integration.md](05-platform-integration.md).
For live vs mock generation, see [08-live-agent-generation.md](08-live-agent-generation.md).

## Mental Model

`edd-agent-lab` is the local authoring and evidence workspace.

`eval-driven-design-platform` is the canonical persistence, gate, promotion, and
observability boundary.

```text
edd-agent-lab  ->  eval-driven-design-platform  ->  Langfuse
```

The lab can run standalone. When the platform API is configured, the lab
publishes run evidence through the platform integration endpoint.

## Local Builder

Start the builder API:

```bash
uv run --extra web uvicorn edd_agent_lab.api.builder:app --host 127.0.0.1 --port 8002
```

Start the React builder:

```bash
cd web/agent-builder
npm run dev
```

Open:

```text
http://localhost:5173
```

The builder flow:

1. Create a draft agent from a name and purpose.
2. Generate and review design artifacts.
3. Add a local scenario.
4. Run v0.
5. Evaluate v0.
6. Generate a fix plan.
7. Generate and run v1.
8. Evaluate v1.
9. Compare v0 and v1.
10. Publish evidence to the platform when configured.

Draft projects live under:

```text
lab-runs/<agent_key>/draft/
```

The UI can review, edit, delete, and regenerate local draft artifacts.

## CLI Workflow

The CLI still supports reference agents, scenarios, eval suites, and publish
smoke tests.

Run an agent version:

```bash
edd-lab run-agent \
  --agent customer-solution \
  --version v1 \
  --scenario healthcare_documentation \
  --generation-mode mock
```

Run evals:

```bash
edd-lab run-evals \
  --agent customer-solution \
  --version v1 \
  --suite discovery_quality
```

Publish a run record:

```bash
edd-lab publish-run --agent customer-solution --version v1
```

If the platform API is unavailable, publish payloads are queued locally under:

```text
lab-runs/_platform_publish_queue/
```

## Generation Modes

| Mode | Behavior |
|---|---|
| `mock` | deterministic local generation |
| `live` | provider-backed generation when credentials are available |
| `auto` | live if credentials exist, otherwise mock |

Tests force mock generation so CI does not require provider keys.

## Platform Workflow

The platform repo owns durable workflow state:

- agent targets
- behavior rules
- eval contracts
- experiment runs
- gate results
- promotion records
- Langfuse integration

Lab artifacts do not become platform records until they are published through the
integration client.

## Friction Points

1. Draft artifacts are local until publish integration is wired for the desired
   platform object.
2. Live generation is opt-in and should not be required for deterministic tests.
3. Publish requires the platform API and auth settings when platform auth is
   enabled.
4. Draft agents are not production-ready just because local evals pass.

## What Works Well

- local draft creation from an idea
- deterministic v0/v1 run and eval loop
- editable artifact review
- local project deletion and regeneration
- platform publish boundary through `POST /v1/integrations/runs/publish`

## Related Docs

| Doc | Topic |
|---|---|
| [03-evaluation-driven-design.md](03-evaluation-driven-design.md) | EDD principles |
| [05-platform-integration.md](05-platform-integration.md) | Ownership and publish envelope |
| [08-live-agent-generation.md](08-live-agent-generation.md) | Mock, live, and auto modes |
| [13-functional-application-plan.md](13-functional-application-plan.md) | Active application backlog |
| [14-react-builder-pivot.md](14-react-builder-pivot.md) | Builder architecture |
