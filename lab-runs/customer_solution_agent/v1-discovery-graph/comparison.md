# v0 -> v1 Comparison

## Change
v1 replaced the broad v0 flow with a discovery-first graph:
`intake -> clarify_problem -> identify_workflow -> identify_stakeholders -> define_success_metrics -> propose_solution -> review_risks -> create_pilot_plan -> create_eval_plan -> final_response`.

## Why This Change
v0 could produce plausible output, but it often relied on generic structure. The bounded goal for v1 was to force explicit discovery steps before solutioning.

## Evaluation Evidence

### Discovery Suite Scores
| Metric / Check | v0 | v1 | Change |
|---|---:|---:|---:|
| Overall discovery score | 1.000 | 1.000 | +0.000 |
| asks_clarifying_questions | 1.000 | 1.000 | +0.000 |
| defines_success_metrics | 1.000 | 1.000 | +0.000 |
| identifies_workflow | 1.000 | 1.000 | +0.000 |
| includes_risks | 1.000 | 1.000 | +0.000 |

### Structural Depth (from run artifacts)
| Signal | v0 | v1 | Change |
|---|---:|---:|---:|
| Discovery questions | 3 | 4 | +1 |
| Stakeholders listed | 0 (`TBD`) | 4 | +4 |
| Workflow decomposition | placeholder | explicit step-by-step flow | improved |
| Data/integration assumptions | 0 (`TBD`) | 3 | +3 |

## Interpretation
The headline score is flat because both runs used heuristic fallback judging (`method: heuristic`, no LLM judge key), which saturates easily on section presence.  
However, artifact-level evidence shows v1 is materially more specific and discovery-oriented than v0.

## Decision
**Accepted with caveat.**  
Accept the v1 graph structure change as a bounded implementation improvement, but do **not** claim a proven quality gain yet from the current discovery score alone.

## Remaining Gaps
- Re-run `discovery_quality` with true LLM-as-judge enabled to validate qualitative gain.
- Add stricter deterministic checks so placeholders (`TBD`) cannot score as fully as concrete content.
- Milestone 5 still required: overfitting/generalization across domain variants.
