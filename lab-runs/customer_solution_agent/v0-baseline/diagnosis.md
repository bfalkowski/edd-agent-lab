# Diagnosis: v0 Baseline

## Summary

The v0 agent produces a plausible solution brief, but it does not reliably perform discovery before solutioning.

## Evidence

- The discovery quality suite scored 0.58 (placeholder until eval runner is implemented).
- The success metrics check failed.
- The response mentioned productivity but did not define how improvement would be measured.
- The risk review was generic and not tied to workflow, compliance, or adoption.

## Likely Cause

The agent is implemented as a single broad prompt. It has no graph-level pressure to complete discovery steps before generating a solution.

## Recommended Fix

Refactor the agent into a discovery-first LangGraph flow with separate nodes for problem clarification, workflow identification, success metrics, risk review, pilot planning, and eval planning.

## Verification Plan

Run the same discovery quality suite after the graph refactor and compare the score against v0.
