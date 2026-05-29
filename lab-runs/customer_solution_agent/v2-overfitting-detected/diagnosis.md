# Diagnosis: v2 Overfitting

## Summary

v1 discovery graph behavior passes the healthcare base case but generalizes poorly across domain-swap variants when scored against scenario-specific discovery themes.

## Evidence

- Suite: `overfitting`
- Evaluated agent: `v1-discovery-graph`
- Base case passed: yes
- Variant pass rate: 0.40 (2/5 variants)
- Overfitting risk: **high**
- Failed variants: `banking_fraud_variant`, `manufacturing_support_variant`, `hr_policy_variant`

See `eval-summary-overfitting.json` and `failure-packet.json`.

## Root Cause

Discovery structure is consistent, but scenario-specific competency vocabulary is missing on several non-healthcare variants. The agent over-indexes on generic discovery scaffolding instead of domain theme coverage.

## Recommended Fix

Introduce a domain-neutral discovery competency model (v3) that maps each scenario's `expected_themes` into discovery questions, stakeholders, risks, and final brief sections before solutioning.
