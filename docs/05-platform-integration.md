# Platform Integration Boundary

## Ownership Boundary

`edd-agent-lab` owns:

- LangGraph agents
- Agent versions
- Scenarios
- Local eval suites for lab experiments
- Local lab-run artifacts and narratives

`eval-driven-design-platform` owns:

- Reusable eval infrastructure
- Experiment/run registry
- Quality gates
- Cross-run comparison
- Durable storage for eval results
- Langfuse integration
- MCP tools for external agents

## Dependency Direction

```text
edd-agent-lab ---> eval-driven-design-platform
```

The platform must not depend on this repo.

## Integration Path (Phased)

1. Local JSON/YAML artifacts (default)
2. Publish envelopes through `integrations/edd_client.py` (`LocalEDDClient`, `HttpEDDClient`, queue fallback)
3. Invoke platform capabilities through `integrations/mcp_client.py` (local shims today; remote MCP optional)

## Publish Envelope

Lab runs publish a versioned envelope (`schema_version: "1"`) built by `integrations/publish.py`:

- `run_id`, `agent`, `agent_version`, `suite`, `scenario_ids`
- `eval_summary`, `failure_packet`, `outputs`, `artifact_paths`

CLI:

```bash
edd-lab publish-run --agent customer-solution --version v3
edd-lab run-evals --agent customer-solution --version v3 --suite overfitting --publish
```

HTTP publish target (platform ingest seam):

```text
POST /v1/integrations/runs/publish
```

Legacy alias (deprecated): `POST /v1/integrations/lab/publish`

If the platform endpoint is unavailable, envelopes are queued under `lab-runs/_platform_publish_queue/`.

## Configure HTTP publish

Lab defaults to `LocalEDDClient` (no network). Set in `.env` or export before `publish-run`:

| Variable | Purpose |
|----------|---------|
| `EDD_CLIENT_MODE` | `http` (or `auto` with `EDD_API_BASE_URL` set) |
| `EDD_API_BASE_URL` | Platform API, e.g. `http://127.0.0.1:8000` |
| `EDD_TENANT_ID` | Tenant on publish envelope (e.g. `tenant-a`) |
| `EDD_EVAL_SPEC_ID` | Platform EvalSpec UUID (create in console or via API) |
| `EDD_API_KEY` | Bearer JWT when platform `APP_AUTH_ENABLED=true` |

`local_e2e.sh` enables auth by default. Use the demo token from script output, set `EDD_API_KEY`, or point `EDD_TOKEN_FILE` at `/tmp/edd-api.token`.

**Verify:**

```bash
./scripts/test_platform_publish.sh
```

The smoke script mints a fresh JWT when `eval-driven-design-platform` is a sibling directory. Expect `published_http` and gate fields in CLI output.

## Platform response

Publish returns `platform_run_id`, `gate_status`, and `gate_explanation`. The platform stores provenance on `ExperimentRun.ingest` (`source`, `external_run_id`, suite, gate). Query gates later via `GET /v1/experiment-runs/{id}/gate`.

## Langfuse Rule

`edd-agent-lab` should not send traces directly to Langfuse.
It publishes run/eval artifacts to the EDD platform; the platform handles
Langfuse trace and score integration.
