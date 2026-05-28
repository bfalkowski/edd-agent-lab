# Fix Plan: v1 Discovery Graph

## Goal

Improve discovery quality by replacing the broad baseline flow with a structured discovery-first graph.

## Bounded Change

Implement v1 with dedicated nodes for:

- clarify_problem
- identify_workflow
- identify_stakeholders
- define_success_metrics
- review_risks
- create_pilot_plan
- create_eval_plan

## Out of Scope

- No MCP integration yet
- No Langfuse integration yet
- No UI
- No automatic code repair agent

## Verification

Run:

```bash
edd-lab run-evals --agent customer-solution --version v0 --suite discovery_quality
edd-lab run-evals --agent customer-solution --version v1 --suite discovery_quality
edd-lab compare-runs \
  --before lab-runs/customer_solution_agent/v0-baseline/eval-summary-discovery_quality.json \
  --after lab-runs/customer_solution_agent/v1-discovery-graph/eval-summary-discovery_quality.json
```

Accept the change only if:

- overall discovery score improves
- clarifying/workflow checks do not regress
- risk coverage remains at least as strong as v0
