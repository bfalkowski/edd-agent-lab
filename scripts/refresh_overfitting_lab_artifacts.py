#!/usr/bin/env python3
"""Refresh v2/v3 lab-run artifacts from latest overfitting eval executions."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.paths import LAB_RUNS_DIR

AGENT_DIR = LAB_RUNS_DIR / "customer_solution_agent"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _copy_if_exists(source: Path, dest: Path) -> None:
    if source.is_file():
        shutil.copy2(source, dest)


def refresh_v2_from_v1() -> dict[str, object]:
    result = run_eval_suite(
        agent_key="customer-solution",
        suite_id="overfitting",
        agent_version="v1-discovery-graph",
    )
    summary = dict(result.summary)
    summary["milestone"] = "v2-overfitting-detected"
    summary["evaluated_agent_version"] = "v1-discovery-graph"

    v2_dir = AGENT_DIR / "v2-overfitting-detected"
    v2_dir.mkdir(parents=True, exist_ok=True)
    _write_json(v2_dir / "eval-summary.json", summary)
    _write_json(v2_dir / "eval-summary-overfitting.json", summary)

    v1_dir = AGENT_DIR / "v1-discovery-graph"
    _copy_if_exists(v1_dir / "failure-packet.json", v2_dir / "failure-packet.json")
    _copy_if_exists(
        v1_dir / "failure-packet-overfitting.json",
        v2_dir / "failure-packet-overfitting.json",
    )
    if result.failure_packet_path and result.failure_packet_path.is_file():
        packet = json.loads(result.failure_packet_path.read_text(encoding="utf-8"))
        packet["milestone"] = "v2-overfitting-detected"
        packet["evaluated_agent_version"] = "v1-discovery-graph"
        _write_json(v2_dir / "failure-packet.json", packet)

    return summary


def refresh_v3() -> dict[str, object]:
    result = run_eval_suite(
        agent_key="customer-solution",
        suite_id="overfitting",
        agent_version="v3-competency-model",
    )
    v3_dir = AGENT_DIR / "v3-competency-model"
    v3_dir.mkdir(parents=True, exist_ok=True)
    _write_json(v3_dir / "eval-summary.json", dict(result.summary))
    _write_json(v3_dir / "eval-summary-overfitting.json", dict(result.summary))
    if result.failure_packet_path and result.failure_packet_path.is_file():
        shutil.copy2(result.failure_packet_path, v3_dir / "failure-packet.json")
    elif (v3_dir / "failure-packet.json").is_file():
        (v3_dir / "failure-packet.json").unlink()
    return dict(result.summary)


def write_v3_comparison(v2_summary: dict[str, object], v3_summary: dict[str, object]) -> None:
    v2_rate = float(v2_summary.get("variant_pass_rate", 0.0))
    v3_rate = float(v3_summary.get("variant_pass_rate", 0.0))
    v2_risk = v2_summary.get("overfitting_risk", "unknown")
    v3_risk = v3_summary.get("overfitting_risk", "unknown")
    delta = round(v3_rate - v2_rate, 3)
    accepted = v3_rate >= 0.8 and v3_risk in {"low", "medium"}

    lines = [
        "# Comparison: v2 → v3",
        "",
        "## Change",
        "v3 adds a domain-neutral discovery competency model before the discovery graph steps.",
        "",
        "## Why This Change",
        (
            "v1 passed the healthcare base case but failed domain-swap variants "
            f"(variant pass rate {v2_rate:.3f}, overfitting risk {v2_risk})."
        ),
        "",
        "## Evaluation Evidence",
        "| Metric | v2 (v1 evaluated) | v3 | Change |",
        "|---|---:|---:|---:|",
        f"| Variant pass rate | {v2_rate:.3f} | {v3_rate:.3f} | {delta:+.3f} |",
        f"| Overfitting risk | {v2_risk} | {v3_risk} | improved |",
        (
            "| Behavioral consistency | "
            f"{float(v2_summary.get('behavioral_consistency_score', 0)):.3f} | "
            f"{float(v3_summary.get('behavioral_consistency_score', 0)):.3f} | — |"
        ),
        "",
        "## Interpretation",
        (
            "Competency-driven discovery improves cross-domain generalization."
            if accepted
            else "v3 did not yet clear the overfitting gate."
        ),
        "",
        "## Decision",
        "Accepted" if accepted else "Needs more work",
        "",
        "## Remaining Gaps",
        "- Platform publish and MCP integration remain deferred (Milestones 7–8).",
        "- Tool-enhanced workflows are still planned for v4.",
    ]
    path = AGENT_DIR / "v3-competency-model" / "comparison.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    v2_summary = refresh_v2_from_v1()
    v3_summary = refresh_v3()
    write_v3_comparison(v2_summary, v3_summary)
    print("v2 variant_pass_rate", v2_summary["variant_pass_rate"], v2_summary["overfitting_risk"])
    print("v3 variant_pass_rate", v3_summary["variant_pass_rate"], v3_summary["overfitting_risk"])


if __name__ == "__main__":
    main()
