from __future__ import annotations

from edd_agent_lab.evals.scorecard import suite_scorecard_rows


def test_suite_scorecard_rows_for_standard_suite() -> None:
    summary = {
        "cases": [
            {
                "case_id": "case_a",
                "scenario": "healthcare_documentation",
                "score": 0.9,
                "checks": [{"passed": True}, {"passed": False}],
            }
        ]
    }
    rows = suite_scorecard_rows(summary)
    assert len(rows) == 1
    assert rows[0].item_id == "case_a"
    assert rows[0].passed is False
    assert rows[0].detail == "1/2 checks"


def test_suite_scorecard_rows_for_overfitting_suite() -> None:
    summary = {
        "base_case_passed": True,
        "base_case": {
            "id": "base_healthcare_documentation",
            "scenario": "healthcare_documentation",
            "score": 1.0,
        },
        "variants": [
            {
                "id": "legal_review_variant",
                "scenario": "legal_review",
                "score": 0.8,
                "passed": True,
                "mutation_type": "domain_swap",
            }
        ],
    }
    rows = suite_scorecard_rows(summary)
    assert len(rows) == 2
    assert rows[0].item_id == "base_healthcare_documentation"
    assert rows[1].scenario == "legal_review"
