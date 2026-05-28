# v0 — Baseline Agent Narrative

## What v0 Does

v0 runs a simple baseline flow that produces a plausible solution brief from one scenario input.

## Evals Run

- `discovery_quality`
- `baseline`

## What Passed

- The response usually includes a coherent proposal, success metrics, risks, and a pilot/eval section.

## What Scored Weakly

- Discovery discipline is shallow and inconsistent.
- Workflow and stakeholder framing are not reliably established before solutioning.
- Current heuristic scoring can saturate on section presence, so high numeric score does not guarantee deep discovery quality.

## Why This Matters

The agent can sound polished while skipping key discovery work. That creates risk of proposing the wrong scope and weakly measurable outcomes.

## Bounded Change Attempted in v1

v1 replaces the broad baseline flow with explicit discovery-first graph nodes. See `fix-plan.md`.
