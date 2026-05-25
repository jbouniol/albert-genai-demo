"""Phase 5 stability — runs each profile N times against the real API.

Validates the CLAUDE.md §10 acceptance criteria:
    - Lucas score > 0.65 on 10/10 runs
    - Emma  score < 0.40 on 10/10 runs
    - Mia   has ≥1 harassment-category signal on ≥ 8/10 runs

Side benefit: the first successful run per (profile, agent) is persisted to
`data/llm_cache/` by CachedLLMClient — but we DON'T use cached mode here
(point of stability is to test non-determinism of real LLM calls). Cache is
seeded separately by `--seed-cache` flag.

Usage:
    python scripts/stability_run.py                  # default 10 runs, all profiles
    python scripts/stability_run.py --runs 5
    python scripts/stability_run.py --profiles lucas
    python scripts/stability_run.py --seed-cache     # also persist outputs to cache
    python scripts/stability_run.py --runs 1 --seed-cache --profiles lucas,emma,mia
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from sentinel.agents.analyzer import Analyzer  # noqa: E402
from sentinel.agents.collector import Collector  # noqa: E402
from sentinel.agents.communicator import Communicator  # noqa: E402
from sentinel.agents.scorer import Scorer  # noqa: E402
from sentinel.config import HITL_TRIGGER  # noqa: E402
from sentinel.data.models import AnalysisResult, ScoreResult  # noqa: E402
from sentinel.llm.cache import CACHE_DIR, CachedLLMClient  # noqa: E402
from sentinel.llm.client import SentinelLLMError  # noqa: E402

console = Console()

ALL_PROFILES = ("lucas", "emma", "mia")

# Hard asserts per profile (CLAUDE.md §10)
ASSERTS = {
    "lucas": {
        "score_min": HITL_TRIGGER,         # > 0.65 on EVERY run
        "score_max": None,
        "require_category": "grooming",    # on ≥80% of runs
        "category_min_runs_pct": 0.80,
        "all_or_nothing_score": True,      # 10/10 not 8/10
    },
    "emma": {
        "score_min": None,
        "score_max": 0.40,                 # < 0.40 on EVERY run
        "require_category": None,
        "category_min_runs_pct": None,
        "all_or_nothing_score": True,
    },
    "mia": {
        "score_min": 0.45,
        "score_max": 0.80,
        "require_category": "harassment",
        "category_min_runs_pct": 0.80,
        "all_or_nothing_score": False,     # 9/10 acceptable for the score range
    },
}


def _make_client(agent_name: str, profile_id: str, seed_cache: bool):
    """Return CachedLLMClient if seeding, else None (= default live LLMClient)."""
    from sentinel.config import MODELS

    if seed_cache:
        # CachedLLMClient persists output to disk on cache miss → seeds the cache
        # WITHOUT short-circuiting subsequent runs (we'll wipe the file between runs)
        return CachedLLMClient(
            model=MODELS[agent_name],
            agent_name=agent_name,
            profile_id=profile_id,
        )
    return None


def _wipe_cache(profile_id: str) -> None:
    """Remove any cached output for the profile so the next run hits the API."""
    profile_dir = CACHE_DIR / profile_id
    if not profile_dir.exists():
        return
    for f in profile_dir.iterdir():
        f.unlink()


def _run_once(profile_id: str, seed_cache: bool) -> tuple[AnalysisResult, ScoreResult, str | None]:
    """One full pipeline run; returns (analysis, score, notification|None)."""
    window = Collector().run(profile_id)
    analysis = Analyzer(client=_make_client("analyzer", profile_id, seed_cache)).run(window)
    score = Scorer(client=_make_client("scorer", profile_id, seed_cache)).run(window, analysis)
    notif = None
    if score.score > HITL_TRIGGER:
        notif = Communicator(client=_make_client("communicator", profile_id, seed_cache)).run(
            window, score
        )
    return analysis, score, notif


def _evaluate(profile_id: str, results: list[dict]) -> tuple[bool, list[str]]:
    """Return (passed, list_of_failure_messages)."""
    rules = ASSERTS[profile_id]
    failures: list[str] = []
    n = len(results)
    scores = [r["score"] for r in results]
    cats: list[set[str]] = [{s.category for s in r["signals"]} for r in results]

    if rules["score_min"] is not None:
        ok_runs = sum(1 for s in scores if s > rules["score_min"])
        threshold = n if rules["all_or_nothing_score"] else int(n * 0.9)
        if ok_runs < threshold:
            failures.append(
                f"score > {rules['score_min']}: {ok_runs}/{n} runs (need ≥ {threshold})"
            )

    if rules["score_max"] is not None:
        ok_runs = sum(1 for s in scores if s < rules["score_max"])
        threshold = n if rules["all_or_nothing_score"] else int(n * 0.9)
        if ok_runs < threshold:
            failures.append(
                f"score < {rules['score_max']}: {ok_runs}/{n} runs (need ≥ {threshold})"
            )

    if rules["require_category"]:
        cat = rules["require_category"]
        ok_runs = sum(1 for c in cats if cat in c)
        threshold = int(n * rules["category_min_runs_pct"])
        if ok_runs < threshold:
            failures.append(
                f"category '{cat}' present: {ok_runs}/{n} runs (need ≥ {threshold})"
            )

    return (len(failures) == 0, failures)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stability run for Sentinel pipeline.")
    parser.add_argument("--runs", type=int, default=10, help="Runs per profile (default 10).")
    parser.add_argument(
        "--profiles",
        type=str,
        default=",".join(ALL_PROFILES),
        help="Comma-separated profile IDs.",
    )
    parser.add_argument(
        "--seed-cache",
        action="store_true",
        help="Persist outputs to data/llm_cache/ on the FIRST run of each profile.",
    )
    args = parser.parse_args(argv)

    profiles = [p.strip() for p in args.profiles.split(",") if p.strip() in ALL_PROFILES]
    if not profiles:
        console.print("[red]No valid profiles selected.[/]")
        return 1

    console.rule("[bold cyan]Sentinel stability run[/]")
    console.print(
        f"profiles: {profiles}  ·  runs each: {args.runs}  ·  "
        f"seed_cache: {args.seed_cache}"
    )
    console.print()

    table = Table(title="Per-run results", show_lines=False)
    table.add_column("Profile", style="cyan")
    table.add_column("Run", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Level")
    table.add_column("Signals", justify="right")
    table.add_column("Categories")
    table.add_column("Latency", justify="right")
    table.add_column("Status")

    overall_ok = True
    all_results: dict[str, list[dict]] = {p: [] for p in profiles}

    for profile_id in profiles:
        for run_idx in range(1, args.runs + 1):
            # First run with --seed-cache : wipe so we hit the API and persist.
            # Subsequent runs : always wipe, we want fresh API hits regardless.
            if args.seed_cache and run_idx == 1:
                _wipe_cache(profile_id)
            t0 = time.perf_counter()
            try:
                analysis, score, _notif = _run_once(
                    profile_id, seed_cache=(args.seed_cache and run_idx == 1)
                )
                elapsed = time.perf_counter() - t0
            except SentinelLLMError as e:
                console.print(f"[red]✗ {profile_id} run #{run_idx} — {e.kind}: {e.original}[/]")
                overall_ok = False
                table.add_row(
                    profile_id, str(run_idx), "-", "-", "-", "-", "-", f"[red]ERROR {e.kind}[/]"
                )
                continue

            cats = sorted({s.category for s in analysis.signals})
            all_results[profile_id].append(
                {
                    "score": score.score,
                    "level": score.level,
                    "signals": analysis.signals,
                    "categories": cats,
                    "elapsed": elapsed,
                }
            )
            table.add_row(
                profile_id,
                str(run_idx),
                f"{score.score:.2f}",
                score.level,
                str(len(analysis.signals)),
                ",".join(cats) or "—",
                f"{elapsed:.1f}s",
                "[green]ok[/]",
            )

    console.print(table)
    console.print()

    # Summary
    console.rule("[bold]Summary[/]")
    summary = Table(show_lines=False)
    summary.add_column("Profile", style="cyan")
    summary.add_column("Runs", justify="right")
    summary.add_column("Result")
    summary.add_column("Failures")

    for profile_id in profiles:
        results = all_results[profile_id]
        if not results:
            summary.add_row(profile_id, "0", "[red]ALL FAILED[/]", "no successful runs")
            overall_ok = False
            continue
        ok, fails = _evaluate(profile_id, results)
        if not ok:
            overall_ok = False
        summary.add_row(
            profile_id,
            f"{len(results)}/{args.runs}",
            "[green]PASS[/]" if ok else "[red]FAIL[/]",
            " ; ".join(fails) if fails else "—",
        )

    console.print(summary)
    console.print()
    if overall_ok:
        console.print("[bold green]✓ All profiles passed[/]")
        return 0
    console.print("[bold red]✗ Some profiles failed — see Failures column[/]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
