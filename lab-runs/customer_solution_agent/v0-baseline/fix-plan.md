# Fix Plan: v1 Discovery Graph

## Goal

Improve discovery quality by replacing the single broad response node with a structured LangGraph flow.

## Bounded Change

Add dedicated graph nodes for:

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
edd-lab run-evals --agent customer-solution --suite discovery_quality
```

Accept the change only if:

- overall_score improves by at least 0.15
- success_metrics check improves
- risk_review check does not regress
