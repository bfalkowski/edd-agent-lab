# Comparison: v2 → v3

## Change
v3 adds a domain-neutral discovery competency model before the discovery graph steps.

## Why This Change
v1 passed the healthcare base case but failed domain-swap variants (variant pass rate 0.400, overfitting risk high).

## Evaluation Evidence
| Metric | v2 (v1 evaluated) | v3 | Change |
|---|---:|---:|---:|
| Variant pass rate | 0.400 | 1.000 | +0.600 |
| Overfitting risk | high | low | improved |
| Behavioral consistency | 0.773 | 0.864 | — |

## Interpretation
Competency-driven discovery improves cross-domain generalization.

## Decision
Accepted

## Remaining Gaps
- Platform publish and MCP integration remain deferred (Milestones 7–8).
- Tool-enhanced workflows are still planned for v4.
