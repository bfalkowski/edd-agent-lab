import typer
from rich.console import Console
from rich.table import Table

from edd_agent_lab.agents.customer_solution_agent import run_customer_solution_agent
from edd_agent_lab import __version__
from edd_agent_lab.evals.loading import list_eval_suite_ids, load_eval_suite
from edd_agent_lab.evals.runner import run_eval_suite
from edd_agent_lab.scenarios.loading import list_scenario_ids, load_scenario

app = typer.Typer(
    name="edd-lab",
    help="EDD Agent Lab — evolve LangGraph agents through evaluation-driven design.",
    no_args_is_help=True,
)
console = Console()


def _resolve_agent(agent: str) -> str:
    return agent or "customer-solution"


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
) -> None:
    """Run an agent against a scenario and write a run artifact."""
    agent_key = _resolve_agent(agent)
    _ = load_scenario(agent_key, scenario)
    if agent_key not in {"customer-solution", "customer_solution", "customer_solution_agent"}:
        console.print(f"[red]Unsupported agent for now:[/red] {agent_key}")
        raise typer.Exit(code=1)

    result = run_customer_solution_agent(scenario_id=scenario, agent_key=agent_key)
    console.print(f"[green]Run complete:[/green] {result.run_id}")
    console.print(f"[green]Artifact:[/green] {result.output_path}")
    console.print()
    console.print(result.final_response)


@app.command("run-evals")
def run_evals(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent key."),
    suite: str = typer.Option(..., "--suite", help="Eval suite ID."),
) -> None:
    """Run an eval suite and write summary artifacts."""
    agent_key = _resolve_agent(agent)
    _ = load_eval_suite(agent_key, suite)
    result = run_eval_suite(agent_key=agent_key, suite_id=suite)
    console.print(f"[green]Eval run complete:[/green] {result.run_id}")
    console.print(f"[green]Summary:[/green] {result.summary_path}")
    if result.failure_packet_path:
        console.print(f"[yellow]Failure packet:[/yellow] {result.failure_packet_path}")
    console.print(f"[bold]Overall score:[/bold] {result.summary['overall_score']}")


@app.command("compare-runs")
def compare_runs(
    before: str = typer.Option(..., "--before", help="Path to before eval-summary.json."),
    after: str = typer.Option(..., "--after", help="Path to after eval-summary.json."),
) -> None:
    """Compare two eval run summaries (later milestone)."""
    table = Table(title="compare-runs (not implemented)")
    table.add_column("Argument")
    table.add_column("Value")
    table.add_row("before", before)
    table.add_row("after", after)
    console.print(table)
    console.print("[yellow]See Milestone 3+ in the build plan.[/yellow]")
    raise typer.Exit(code=2)


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
