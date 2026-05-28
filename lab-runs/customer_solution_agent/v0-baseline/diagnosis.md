# Diagnosis: v0 Baseline

## Summary

The v0 agent can produce a plausible solution brief, but eval evidence shows discovery behavior is shallow and inconsistent.

## Evidence

- `discovery_quality` now passes structurally, but the response can still jump to solutioning before fully surfacing workflow and stakeholder constraints.
- `baseline` checks demonstrate the core sections are present, but depth quality is uneven.
- The response quality is sensitive to prompt wording and does not consistently force discovery-first reasoning.

## Likely Cause

The baseline flow is broad and lightly constrained. It does not impose explicit graph-level checkpoints for workflow identification, stakeholder mapping, and discovery planning.

## Recommended Fix

Refactor to a discovery-first LangGraph flow with separate nodes for clarification, workflow, stakeholders, metrics, risks, pilot, and eval planning.

## Verification Plan

Run `discovery_quality` for v0 and v1, then compare summaries with `edd-lab compare-runs`.
