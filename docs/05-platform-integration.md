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
POST /v1/integrations/lab/publish
```

If the platform endpoint is unavailable, envelopes are queued under `lab-runs/_platform_publish_queue/`.

## Langfuse Rule

`edd-agent-lab` should not send traces directly to Langfuse.
It publishes run/eval artifacts to the EDD platform; the platform handles
Langfuse trace and score integration.
