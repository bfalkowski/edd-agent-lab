# v1 — Discovery-First Graph

## What Changed from v0

v1 replaces the broad v0 flow with explicit nodes:

- intake
- clarify_problem
- identify_workflow
- identify_stakeholders
- define_success_metrics
- propose_solution
- review_risks
- create_pilot_plan
- create_eval_plan
- final_response

## Why This Was Bounded

The change is limited to graph structure and state progression. It does not add new external tools, MCP, Langfuse, UI, or platform dependencies.

## Eval Suite Rerun

- `discovery_quality`

## Result

v1 improved structural depth, but the latest discovery score is flat versus v0 under heuristic scoring.

## Regressions

No measured regression in the tracked checks for the current scenario.

## Unresolved

- Generalization across domain variants is still untested.
- Overfitting detection is deferred to Milestone 5.
- Current scoring needs stricter quality signals to separate shallow from robust discovery.

See `comparison.md` for metric-level evidence.
