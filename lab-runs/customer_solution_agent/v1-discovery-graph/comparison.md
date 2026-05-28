# v0 -> v1 Comparison
## Change
v1 replaced the broad v0 flow with a discovery-first graph.
## Why This Change
The v0 eval showed weak discovery discipline relative to the target behavior.
## Evaluation Evidence
| Metric / Check | v0 | v1 | Change |
|---|---:|---:|---:|
| Overall discovery score | 1.000 | 1.000 | +0.000 |
| asks_clarifying_questions | 1.000 | 1.000 | +0.000 |
| defines_success_metrics | 1.000 | 1.000 | +0.000 |
| identifies_workflow | 1.000 | 1.000 | +0.000 |
| includes_risks | 1.000 | 1.000 | +0.000 |
## Interpretation
The evidence does not yet support accepting v1 without further refinement.
## Decision
Needs more work
## Remaining Gaps
- Overfitting/generalization across domain variants is not yet tested (Milestone 5).
- Platform API/MCP integration is intentionally deferred.
