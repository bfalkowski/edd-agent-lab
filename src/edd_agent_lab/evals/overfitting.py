"""Overfitting risk scoring helpers."""

from __future__ import annotations


def overfitting_risk(base_case_passed: bool, variant_pass_rate: float) -> str:
    if not base_case_passed:
        return "unknown"
    if variant_pass_rate < 0.50:
        return "high"
    if variant_pass_rate < 0.80:
        return "medium"
    return "low"
