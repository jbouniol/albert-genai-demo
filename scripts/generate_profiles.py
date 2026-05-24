"""Generate the 3 demo profiles as JSON files.

Usage:
    python scripts/generate_profiles.py

Output: src/sentinel/data/profiles/{emma,lucas,mia}.json
Deterministic: same SEED per profile → identical output every run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console  # noqa: E402

from sentinel.data.generator import (  # noqa: E402
    generate_emma_profile,
    generate_lucas_profile,
    generate_mia_profile,
)
from sentinel.data.models import MetadataWindow  # noqa: E402

console = Console()

PROFILES_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "sentinel" / "data" / "profiles"
)


def _stats(profile: MetadataWindow) -> str:
    total_msgs = sum(
        c.message_count for day in profile.days for c in day.contacts_interactions
    )
    total_screen = sum(day.total_screen_time_min for day in profile.days)
    return (
        f"{len(profile.days)} jours · "
        f"{total_msgs} msgs · "
        f"{total_screen} min screen time"
    )


def main() -> int:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "emma": generate_emma_profile,
        "lucas": generate_lucas_profile,
        "mia": generate_mia_profile,
    }
    console.rule("[bold cyan]Génération des profils Sentinel[/]")
    for profile_id, gen in generators.items():
        profile = gen()
        out_path = PROFILES_DIR / f"{profile_id}.json"
        out_path.write_text(profile.model_dump_json(indent=2))
        console.print(f"[green]✓[/] {out_path.name} — {_stats(profile)}")
    console.rule("[bold green]Done[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
