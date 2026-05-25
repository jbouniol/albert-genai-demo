"""Full Sentinel pipeline demo — terminal version.

Runs the complete 4-agent LangGraph pipeline for a chosen profile and renders
all outputs in Rich panels. Use this as fallback if Streamlit is unavailable.

Usage:
    python scripts/run_cli_demo.py <emma|lucas|mia> [--save-graph]

Options:
    --save-graph    Save a PNG of the LangGraph to graph.png (requires internet
                    for mermaid.ink; non-blocking if it fails).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.progress import Progress, SpinnerColumn, TextColumn  # noqa: E402
from rich.rule import Rule  # noqa: E402
from rich.table import Table  # noqa: E402

from sentinel.config import HITL_TRIGGER, THRESHOLDS  # noqa: E402
from sentinel.orchestrator.graph import AgentState, build_graph, save_graph_png  # noqa: E402

console = Console()
VALID_PROFILES = ("emma", "lucas", "mia")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_color(score: float) -> str:
    if score >= THRESHOLDS["high_alert"]:
        return "red"
    if score >= THRESHOLDS["alert"]:
        return "yellow"
    if score >= THRESHOLDS["monitor"]:
        return "cyan"
    return "green"


def _render_score_panel(score_result) -> Panel:
    color = _score_color(score_result.score)
    bar_filled = int(score_result.score * 30)
    bar = f"[{color}]{'█' * bar_filled}[/][dim]{'░' * (30 - bar_filled)}[/]"
    content = (
        f"{bar}\n\n"
        f"[bold {color}]{score_result.level}[/]  "
        f"[bold white]{score_result.score:.2f}[/] / 1.00\n\n"
        f"{score_result.rationale}"
    )
    return Panel(content, title="[bold]Risk Score[/]", border_style=color)


def _render_signals_table(analysis) -> Table | str:
    if not analysis.signals:
        return "[dim]No signals detected.[/]"
    sev_color = {"low": "green", "medium": "yellow", "high": "red"}
    table = Table(title=f"Signals ({len(analysis.signals)})", show_lines=True, expand=True)
    table.add_column("Signal", style="cyan", no_wrap=True)
    table.add_column("Category", style="yellow")
    table.add_column("Sev", justify="center")
    table.add_column("Conf", justify="right")
    table.add_column("Evidence")
    for s in analysis.signals:
        table.add_row(
            s.name,
            s.category,
            f"[{sev_color[s.severity]}]{s.severity}[/]",
            f"{s.confidence:.2f}",
            s.evidence,
        )
    return table


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}

    if len(args) != 1 or args[0] not in VALID_PROFILES:
        console.print(
            f"[red]Usage:[/] python scripts/run_cli_demo.py "
            f"<{'|'.join(VALID_PROFILES)}> [--save-graph]"
        )
        return 1

    profile_id = args[0]
    save_graph = "--save-graph" in flags

    console.print()
    console.print(Rule(f"[bold cyan]SENTINEL DEMO — {profile_id.upper()}[/]"))
    console.print()

    # Optionally save the graph PNG
    if save_graph:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task("Saving graph PNG…", total=None)
            ok = save_graph_png("graph.png")
            p.remove_task(t)
        if ok:
            console.print("[green]✓[/] graph.png saved")
        else:
            console.print("[dim]⚠ graph.png skipped (network or dependency issue)[/]")
        console.print()

    # Build and run the graph
    graph = build_graph()
    initial_state: AgentState = {
        "profile_id": profile_id,
        "window": None,
        "analysis": None,
        "score_result": None,
        "notification": None,
    }

    t0 = time.perf_counter()

    agent_labels = {
        "collector": "Collector   — loading profile",
        "analyzer":  "Analyzer    — detecting signals  (gpt-4o)",
        "scorer":    "Scorer      — computing score    (gpt-4o)",
        "communicator": "Communicator — drafting notification (gpt-4o-mini)",
    }

    final_state: AgentState | None = None

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        active_task = progress.add_task("Starting…", total=None)

        for event in graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                label = agent_labels.get(node_name, node_name)
                progress.update(active_task, description=f"[cyan]{label}[/]")
                if final_state is None:
                    final_state = dict(initial_state)
                assert final_state is not None
                final_state.update(node_output)  # type: ignore[arg-type]

        progress.remove_task(active_task)

    elapsed = time.perf_counter() - t0

    if final_state is None:
        console.print("[red]Pipeline returned no state.[/]")
        return 1

    # ---- Results ----

    console.print()
    console.print(Rule("[bold green]RESULTS[/]"))
    console.print()

    window = final_state.get("window")
    analysis = final_state.get("analysis")
    score_result = final_state.get("score_result")
    notification = final_state.get("notification")

    if window:
        console.print(
            Panel(
                f"[bold]{window.profile_name}[/], {window.age} ans — {window.persona_label}",
                title="Profile",
                border_style="dim",
            )
        )
        console.print()

    if analysis:
        console.print(
            Panel(
                analysis.overall_observation,
                title="[bold]Analyzer — Overall Observation[/]",
                border_style="white",
            )
        )
        console.print()
        nle_color = "green" if analysis.matches_normal_life_event else "yellow"
        console.print(
            f"[{nle_color}]matches_normal_life_event = "
            f"{analysis.matches_normal_life_event}[/]"
        )
        console.print()
        console.print(_render_signals_table(analysis))
        console.print()

    if score_result:
        console.print(_render_score_panel(score_result))
        console.print()

    if notification:
        console.print(
            Panel(
                notification,
                title=f"[bold red]⚠ Parent Notification (score > {HITL_TRIGGER})[/]",
                border_style="red",
            )
        )
        console.print()
    elif score_result and score_result.score <= HITL_TRIGGER:
        console.print(
            f"[dim]Communicator not triggered "
            f"(score {score_result.score:.2f} ≤ threshold {HITL_TRIGGER})[/]"
        )
        console.print()

    console.print(Rule(f"[dim]Done in {elapsed:.1f}s[/]"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
