"""Command-line entry point for QuantSpec."""

import typer

from quant_spec import __version__

app = typer.Typer(
    no_args_is_help=True,
    help="QuantSpec command-line interface.",
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    """Show package metadata and top-level CLI help."""
    if version:
        typer.echo(f"quant-spec {__version__}")
        raise typer.Exit()
