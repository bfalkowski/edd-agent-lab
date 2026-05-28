import json

from typer.testing import CliRunner

from edd_agent_lab.cli.main import _agent_version_to_dirname, app
from edd_agent_lab.paths import LAB_RUNS_DIR

runner = CliRunner()


def test_version_resolver_maps_v0_and_v1() -> None:
    assert _agent_version_to_dirname("v0") == "v0-baseline"
    assert _agent_version_to_dirname("v0-baseline") == "v0-baseline"
    assert _agent_version_to_dirname("v1") == "v1-discovery-graph"
    assert _agent_version_to_dirname("v1-discovery-graph") == "v1-discovery-graph"


def test_run_agent_accepts_version_flag() -> None:
    result = runner.invoke(
        app,
        [
            "run-agent",
            "--agent",
            "customer-solution",
            "--version",
            "v1",
            "--scenario",
            "healthcare_documentation",
        ],
    )
    assert result.exit_code == 0
    assert "v1-discovery-graph" in result.stdout


def test_run_evals_accepts_version_flag() -> None:
    result = runner.invoke(
        app,
        [
            "run-evals",
            "--agent",
            "customer-solution",
            "--version",
            "v0",
            "--suite",
            "discovery_quality",
        ],
    )
    assert result.exit_code == 0
    assert "v0-baseline" in result.stdout


def test_compare_runs_reads_v0_and_v1_summaries() -> None:
    v0_summary = (
        LAB_RUNS_DIR
        / "customer_solution_agent"
        / "v0-baseline"
        / "eval-summary-discovery_quality.json"
    )
    v1_summary = (
        LAB_RUNS_DIR
        / "customer_solution_agent"
        / "v1-discovery-graph"
        / "eval-summary-discovery_quality.json"
    )
    assert v0_summary.is_file()
    assert v1_summary.is_file()

    output = LAB_RUNS_DIR / "customer_solution_agent" / "v1-discovery-graph" / "comparison.md"
    result = runner.invoke(
        app,
        [
            "compare-runs",
            "--before",
            str(v0_summary),
            "--after",
            str(v1_summary),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0
    assert output.is_file()
    content = output.read_text(encoding="utf-8")
    assert "v0 -> v1 Comparison" in content

    v0_data = json.loads(v0_summary.read_text(encoding="utf-8"))
    v1_data = json.loads(v1_summary.read_text(encoding="utf-8"))
    assert v0_data["agent_version"] == "v0-baseline"
    assert v1_data["agent_version"] == "v1-discovery-graph"
