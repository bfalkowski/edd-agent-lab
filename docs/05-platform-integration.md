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

1. Local JSON/YAML artifacts (current default)
2. Publish artifacts through `integrations/edd_client.py` (future HTTP/SDK)
3. Consume platform capabilities via MCP (later milestone)

## Langfuse Rule

`edd-agent-lab` should not send traces directly to Langfuse.
It publishes run/eval artifacts to the EDD platform; the platform handles
Langfuse trace and score integration.
