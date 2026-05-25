"""Run the Analyzer on a profile JSON and print the structured result.

Usage:
    python scripts/run_analyzer.py <emma|lucas|mia>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

from sentinel.agents.analyzer import Analyzer  # noqa: E402
from sentinel.data.models import MetadataWindow  # noqa: E402

console = Console()

PROFILES_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "sentinel" / "data" / "profiles"
)
VALID_PROFILES = ("emma", "lucas", "mia")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in VALID_PROFILES:
        console.print(
            f"[red]Usage:[/] python scripts/run_analyzer.py "
            f"<{'|'.join(VALID_PROFILES)}>"
        )
        return 1

    profile_id = argv[1]
    path = PROFILES_DIR / f"{profile_id}.json"
    window = MetadataWindow.model_validate_json(path.read_text())

    console.rule(f"[bold cyan]Analyzer — {window.profile_name} ({profile_id})[/]")

    analyzer = Analyzer()
    result = analyzer.run(window)

    console.print()
    console.rule("[bold green]Résultat[/]")
    console.print(
        Panel(result.overall_observation, title="Overall observation", border_style="white")
    )

    if result.signals:
        table = Table(title=f"Signals détectés ({len(result.signals)})", show_lines=True)
        table.add_column("Signal", style="cyan", no_wrap=True)
        table.add_column("Catégorie", style="yellow")
        table.add_column("Sévérité")
        table.add_column("Conf", justify="right")
        table.add_column("Evidence")
        sev_color = {"low": "green", "medium": "yellow", "high": "red"}
        for s in result.signals:
            table.add_row(
                s.name,
                s.category,
                f"[{sev_color[s.severity]}]{s.severity}[/]",
                f"{s.confidence:.2f}",
                s.evidence,
            )
        console.print(table)
    else:
        console.print("[dim]Aucun signal détecté.[/]")

    flag_color = "green" if result.matches_normal_life_event else "yellow"
    console.print(
        f"\n[{flag_color}]matches_normal_life_event = "
        f"{result.matches_normal_life_event}[/]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
