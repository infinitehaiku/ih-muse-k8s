# ih_muse_k8s/cli.py
import typer
from rich.console import Console

from ih_muse_k8s.config import ElementKind, MetricCode

app = typer.Typer()
console = Console()


@app.command()
def show_config() -> None:
    console.print("Element Kinds:")
    for ek in ElementKind:
        console.print(f"- {ek.value}")

    console.print("Metric Codes:")
    for mc in MetricCode:
        console.print(f"- {mc.value}")


if __name__ == "__main__":
    app()
