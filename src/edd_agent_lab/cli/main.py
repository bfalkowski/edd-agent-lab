from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from edd_agent_lab import __version__
from edd_agent_lab.agents.customer_solution_agent import run_customer_solution_agent
from edd_agent_lab.evals.loading import list_eval_suite_ids, load_eval_suite
from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.integrations.edd_client import get_edd_client, publish_run_record_file
from edd_agent_lab.paths import LAB_RUNS_DIR
from edd_agent_lab.scenarios.loading import list_scenario_ids, load_scenario

app = typer.Typer(
    name="edd-lab",
    help="EDD Agent Lab — evolve LangGraph agents through evaluation-driven design.",
    no_args_is_help=True,
)
console = Console()


def _resolve_agent(agent: str) -> str:
    return agent or "customer-solution"


def _agent_version_to_dirname(agent_version: str) -> str:
    version = agent_version.strip().lower()
    mapping = {
        "v0": "v0-baseline",
        "v0-baseline": "v0-baseline",
        "v1": "v1-discovery-graph",
        "v1-discovery-graph": "v1-discovery-graph",
        "v3": "v3-competency-model",
        "v3-competency-model": "v3-competency-model",
    }
    if version not in mapping:
        raise typer.BadParameter(
            "Unsupported version. Use v0, v1, v3, or explicit directory names "
            "(v0-baseline, v1-discovery-graph, v3-competency-model)."
        )
    return mapping[version]


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
    ),
) -> None:
    if version:
        console.print(f"edd-agent-lab {__version__}")
        raise typer.Exit()


@app.command("list-scenarios")
def list_scenarios_cmd(
    agent: str = typer.Option("customer-solution", "--agent", "-a", help="Agent key."),
) -> None:
    """List available scenario IDs for an agent."""
    agent_key = _resolve_agent(agent)
    ids = list_scenario_ids(agent_key)
    if not ids:
        console.print(f"No scenarios found for agent [bold]{agent_key}[/bold].")
        raise typer.Exit(code=1)
    for scenario_id in ids:
        scenario = load_scenario(agent_key, scenario_id)
        console.print(f"  {scenario.id} — {scenario.title}")


@app.command("list-evals")
def list_evals_cmd(
    agent: str = typer.Option("customer-solution", "--agent", "-a", help="Agent key."),
) -> None:
    """List available eval suite IDs for an agent."""
    agent_key = _resolve_agent(agent)
    ids = list_eval_suite_ids(agent_key)
    if not ids:
        console.print(f"No eval suites found for agent [bold]{agent_key}[/bold].")
        raise typer.Exit(code=1)
    for suite_id in ids:
        suite = load_eval_suite(agent_key, suite_id)
        desc = suite.description.strip().replace("\n", " ")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        console.print(f"  {suite.id} — {desc}")


@app.command("run-agent")
def run_agent(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent key."),
    scenario: str = typer.Option(..., "--scenario", "-s", help="Scenario ID."),
    agent_version: str = typer.Option(
        "v0",
        "--version",
        "--agent-version",
        help="Agent version (v0|v1) or explicit directory name.",
    ),
    generation_mode: str | None = typer.Option(
        None,
        "--generation-mode",
        help="Agent generation mode: mock, live, or auto (default: env or auto).",
    ),
) -> None:
    """Run an agent against a scenario and write a run artifact."""
    agent_key = _resolve_agent(agent)
    _ = load_scenario(agent_key, scenario)
    if agent_key not in {"customer-solution", "customer_solution", "customer_solution_agent"}:
        console.print(f"[red]Unsupported agent for now:[/red] {agent_key}")
        raise typer.Exit(code=1)

    version_dir = _agent_version_to_dirname(agent_version)
    result = run_customer_solution_agent(
        scenario_id=scenario,
        agent_key=agent_key,
        agent_version=version_dir,
        generation_mode=generation_mode,
    )
    console.print(f"[green]Run complete:[/green] {result.run_id}")
    console.print(f"[bold]Agent version:[/bold] {version_dir}")
    console.print(f"[bold]Generation mode:[/bold] {result.generation_mode}")
    console.print(f"[green]Artifact:[/green] {result.output_path}")
    console.print()
    console.print(result.final_response)


@app.command("run-evals")
def run_evals(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent key."),
    suite: str = typer.Option(..., "--suite", help="Eval suite ID."),
    agent_version: str = typer.Option(
        "v0",
        "--version",
        "--agent-version",
        help="Agent version (v0|v1) or explicit directory name.",
    ),
    publish: bool = typer.Option(
        False,
        "--publish",
        help="Publish run-record to EDD platform (or local publish queue).",
    ),
) -> None:
    """Run an eval suite and write summary artifacts."""
    agent_key = _resolve_agent(agent)
    _ = load_eval_suite(agent_key, suite)
    version_dir = _agent_version_to_dirname(agent_version)
    result = run_eval_suite(agent_key=agent_key, suite_id=suite, agent_version=version_dir)
    console.print(f"[green]Eval run complete:[/green] {result.run_id}")
    console.print(f"[bold]Agent version:[/bold] {version_dir}")
    console.print(f"[green]Summary:[/green] {result.summary_path}")
    if result.failure_packet_path:
        console.print(f"[yellow]Failure packet:[/yellow] {result.failure_packet_path}")
    console.print(f"[bold]Overall score:[/bold] {result.summary['overall_score']}")
    if publish:
        _publish_latest_run_record(agent_key=agent_key, version_dir=version_dir)


def _agent_lab_dir(agent_key: str, version_dir: str) -> Path:
    mapping = {
        "customer-solution": "customer_solution_agent",
        "customer_solution": "customer_solution_agent",
        "customer_solution_agent": "customer_solution_agent",
    }
    dirname = mapping.get(agent_key, agent_key.replace("-", "_"))
    return LAB_RUNS_DIR / dirname / version_dir


def _publish_latest_run_record(agent_key: str, version_dir: str) -> None:
    run_record_path = _agent_lab_dir(agent_key, version_dir) / "run-record.json"
    if not run_record_path.is_file():
        console.print(f"[red]Run record not found:[/red] {run_record_path}")
        raise typer.Exit(code=1)
    publish_result = publish_run_record_file(run_record_path, client=get_edd_client())
    console.print(f"[green]Publish status:[/green] {publish_result.get('status')}")
    if publish_result.get("queue_path"):
        console.print(f"[yellow]Queued at:[/yellow] {publish_result['queue_path']}")
    if publish_result.get("platform_run_id"):
        console.print(f"[bold]Platform run id:[/bold] {publish_result['platform_run_id']}")


@app.command("publish-run")
def publish_run(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent key."),
    version: str = typer.Option(..., "--version", help="Agent version alias or directory."),
    run_record: str | None = typer.Option(
        None,
        "--run-record",
        help="Optional path to run-record.json (defaults to latest lab run).",
    ),
) -> None:
    """Publish a local lab run record to the EDD platform ingest seam."""
    agent_key = _resolve_agent(agent)
    version_dir = _agent_version_to_dirname(version)
    run_record_path = (
        Path(run_record)
        if run_record
        else _agent_lab_dir(agent_key, version_dir) / "run-record.json"
    )
    if not run_record_path.is_file():
        console.print(f"[red]Run record not found:[/red] {run_record_path}")
        raise typer.Exit(code=1)
    publish_result = publish_run_record_file(run_record_path, client=get_edd_client())
    console.print(f"[green]Publish status:[/green] {publish_result.get('status')}")
    if publish_result.get("queue_path"):
        console.print(f"[yellow]Queued at:[/yellow] {publish_result['queue_path']}")
    if publish_result.get("platform_run_id"):
        console.print(f"[bold]Platform run id:[/bold] {publish_result['platform_run_id']}")


@app.command("compare-runs")
def compare_runs(
    before: str = typer.Option(..., "--before", help="Path to before eval-summary.json."),
    after: str = typer.Option(..., "--after", help="Path to after eval-summary.json."),
    output: str | None = typer.Option(
        None,
        "--output",
        help="Optional output markdown path for comparison report.",
    ),
) -> None:
    """Compare two eval run summaries and print deltas."""
    import json
    from pathlib import Path

    before_path = Path(before)
    after_path = Path(after)
    before_data = json.loads(before_path.read_text(encoding="utf-8"))
    after_data = json.loads(after_path.read_text(encoding="utf-8"))

    before_score = float(before_data.get("overall_score", 0.0))
    after_score = float(after_data.get("overall_score", 0.0))
    delta = round(after_score - before_score, 3)

    table = Table(title="Eval Comparison")
    table.add_column("Metric")
    table.add_column("Before")
    table.add_column("After")
    table.add_column("Delta")
    table.add_row("overall_score", f"{before_score:.3f}", f"{after_score:.3f}", f"{delta:+.3f}")

    before_cases = {case["case_id"]: case for case in before_data.get("cases", [])}
    after_cases = {case["case_id"]: case for case in after_data.get("cases", [])}
    for case_id in sorted(set(before_cases) | set(after_cases)):
        b_score = float(before_cases.get(case_id, {}).get("score", 0.0))
        a_score = float(after_cases.get(case_id, {}).get("score", 0.0))
        table.add_row(case_id, f"{b_score:.3f}", f"{a_score:.3f}", f"{(a_score-b_score):+.3f}")

    console.print(table)
    if output:
        output_path = Path(output)
    else:
        output_path = after_path.parent / "comparison.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    common_checks = []
    if before_data.get("cases") and after_data.get("cases"):
        b_checks = {
            item["id"]: item.get("score", 0.0)
            for item in before_data["cases"][0].get("checks", [])
        }
        a_checks = {
            item["id"]: item.get("score", 0.0)
            for item in after_data["cases"][0].get("checks", [])
        }
        for check_id in sorted(set(b_checks) | set(a_checks)):
            b_val = float(b_checks.get(check_id, 0.0))
            a_val = float(a_checks.get(check_id, 0.0))
            delta_check = a_val - b_val
            common_checks.append(
                f"| {check_id} | {b_val:.3f} | {a_val:.3f} | {delta_check:+.3f} |"
            )

    md_lines = [
        "# v0 -> v1 Comparison",
        "## Change",
        "v1 replaced the broad v0 flow with a discovery-first graph.",
        "## Why This Change",
        "The v0 eval showed weak discovery discipline relative to the target behavior.",
        "## Evaluation Evidence",
        "| Metric / Check | v0 | v1 | Change |",
        "|---|---:|---:|---:|",
        f"| Overall discovery score | {before_score:.3f} | {after_score:.3f} | {delta:+.3f} |",
    ]
    md_lines.extend(common_checks)
    md_lines.extend(
        [
            "## Interpretation",
            (
                "The evidence supports accepting v1 for discovery_quality."
                if delta > 0
                else "The evidence does not yet support accepting v1 without further refinement."
            ),
            "## Decision",
            "Accepted" if delta > 0 else "Needs more work",
            "## Remaining Gaps",
            "- Overfitting/generalization across domain variants is not yet tested (Milestone 5).",
            "- Platform API/MCP integration is intentionally deferred.",
        ]
    )
    output_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    console.print(f"[green]Comparison report:[/green] {output_path}")


@app.command("compare-turn")
def compare_turn(
    agent: str = typer.Option("customer-solution", "--agent", "-a"),
    scenario: str = typer.Option(..., "--scenario", "-s"),
    suite: str = typer.Option("discovery_quality", "--suite"),
    before: str = typer.Option("v0-baseline", "--before"),
    after: str = typer.Option("v1-discovery-graph", "--after"),
    message: str | None = typer.Option(None, "--message", "-m"),
) -> None:
    """Run one turn on two versions and print turn-level EDD comparison."""
    from edd_agent_lab.agents.customer_solution_agent.runner import run_customer_solution_turn
    from edd_agent_lab.evals.turn_artifacts import new_session_id, new_turn_id, write_turn_artifacts
    from edd_agent_lab.evals.turn_comparison import compare_turn_evaluation
    from edd_agent_lab.evals.turn_evaluator import evaluate_turn

    scenario_obj = load_scenario(_resolve_agent(agent), scenario)
    user_message = message or scenario_obj.problem
    before_version = _agent_version_to_dirname(before)
    after_version = _agent_version_to_dirname(after)

    before_result = run_customer_solution_turn(
        scenario_id=scenario,
        agent_version=before_version,
        user_message=user_message,
    )
    after_result = run_customer_solution_turn(
        scenario_id=scenario,
        agent_version=after_version,
        user_message=user_message,
    )
    evaluation = evaluate_turn(
        agent="customer_solution_agent",
        scenario_id=scenario,
        suite_id=suite,
        user_input=user_message,
        responses_by_version={
            before_version: before_result["final_response"],
            after_version: after_result["final_response"],
        },
    )
    comparison = compare_turn_evaluation(
        evaluation,
        before_version=before_version,
        after_version=after_version,
    )
    artifact_dir = write_turn_artifacts(
        session_id=new_session_id(),
        turn_id=new_turn_id(),
        evaluation=evaluation,
        comparison=comparison,
    )
    console.print(f"[bold]Decision:[/bold] {comparison.decision}")
    console.print(f"[bold]Score delta:[/bold] {comparison.score_delta:+.3f}")
    console.print(comparison.explanation)
    console.print(f"[green]Artifacts:[/green] {artifact_dir}")


@app.command("console")
def launch_console() -> None:
    """Launch the Streamlit side-by-side comparison console."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    from edd_agent_lab.ui.app import LAB_CONSOLE_PORT

    repo_root = Path(__file__).resolve().parents[3]
    src_root = repo_root / "src"
    app_path = Path(__file__).resolve().parents[1] / "ui" / "app.py"
    lab_url = f"http://localhost:{LAB_CONSOLE_PORT}"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(src_root), env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)

    console.print(f"[green]Agent lab console:[/green] {lab_url}")
    console.print(
        "[dim]Platform UI is usually :8501; this lab chat uses :8502.[/dim]"
    )
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app_path),
                "--server.port",
                str(LAB_CONSOLE_PORT),
                "--server.headless",
                "true",
            ],
            check=False,
            cwd=str(repo_root),
            env=env,
        )
    except ModuleNotFoundError:
        console.print("Streamlit not found. Install UI dependencies and run:")
        console.print("  pip install -e '.[ui]'")
        console.print("  edd-lab console")
        raise typer.Exit(code=2) from None


@app.command("invoke-mcp")
def invoke_mcp(
    tool: str = typer.Option(..., "--tool", help="MCP tool name."),
    arguments: str = typer.Option("{}", "--arguments", help="JSON object of tool arguments."),
) -> None:
    """Invoke an EDD MCP tool via local shims (or remote server when configured)."""
    from edd_agent_lab.integrations.mcp_client import invoke_mcp_tool

    result = invoke_mcp_tool(tool, arguments)
    console.print_json(data=result)


@app.command("generate-variants")
def generate_variants(
    scenario: str = typer.Option(..., "--scenario", "-s", help="Base scenario ID."),
    strategies: list[str] = typer.Option(
        [],
        "--strategies",
        help="Mutation strategies (repeat flag for multiple).",
    ),
) -> None:
    """Generate candidate variant scenarios (later milestone)."""
    console.print(f"scenario={scenario} strategies={strategies}")
    console.print("[yellow]See later milestones in the build plan.[/yellow]")
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
