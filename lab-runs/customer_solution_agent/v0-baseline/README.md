# v0 — Naive Prompt Agent

## What changed

Initial baseline: a simple LangGraph agent with a single broad reasoning path (Milestone 2).

## Evals run

- `discovery_quality`
- `baseline`

## Failures (expected)

- Discovery quality: low/medium
- Measurable value: low
- Risk coverage: medium

## Evidence

See `eval-summary.json` (populated after Milestone 3 eval runner).

## Next bounded change

Refactor into a discovery-first LangGraph with dedicated nodes (v1). See `fix-plan.md`.
