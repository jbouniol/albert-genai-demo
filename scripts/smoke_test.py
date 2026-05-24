"""Smoke test — valide les fondations Phase 0.

Usage:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console  # noqa: E402

from sentinel.config import MODELS  # noqa: E402
from sentinel.llm.client import LLMClient  # noqa: E402

console = Console()


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red bold]✗ OPENAI_API_KEY non défini.[/]")
        console.print("Procédure : [cyan]cp .env.example .env[/] puis renseigner ta clé.")
        return 1

    console.rule("[bold cyan]Smoke test — Sentinel Phase 0[/]")
    console.print(f"Modèle : [yellow]{MODELS['collector']}[/]\n")

    client = LLMClient(model=MODELS["collector"])
    response = client.call(
        instructions="Tu es un assistant de test. Réponds en un seul mot.",
        user_input="Dis 'pong' et rien d'autre.",
    )

    console.print()
    console.rule("[bold green]✓ Smoke test OK[/]")
    console.print(f"Réponse parsée : [bold]{response.output_text!r}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
