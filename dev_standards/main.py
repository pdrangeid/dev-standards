import logging

import typer
from rich.console import Console

from dev_standards.registry.cli import registry_app
from dev_standards.workspace.cli import workspace_app

app = typer.Typer()
app.add_typer(workspace_app, name="workspace")
app.add_typer(registry_app, name="registry")
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def run(
    # Add your command arguments here, e.g.:
    # input: str = typer.Option(..., "--input", "-i", help="Input file path."),
    # output: str = typer.Option("output.json", "--output", "-o", help="Output file."),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
):
    """dev-standards — main entry point."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    console.print("[bold green]✅ dev-standards started[/bold green]")
    # TODO: implement


if __name__ == "__main__":
    app()
