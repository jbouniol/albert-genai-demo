"""Baseline computation tool — computes behavioral baseline from days 0-13.

Per CLAUDE.md §3: baseline = first 14 days, sliding window = last 7 days for drift.
"""
from __future__ import annotations

from statistics import mean

from sentinel.data.generator import APPS
from sentinel.data.models import Baseline, MetadataWindow

BASELINE_DAYS = 14


def compute_baseline(window: MetadataWindow) -> Baseline:
    """Aggregate days 0-13 into a stable behavioral baseline."""
    days = window.days[:BASELINE_DAYS]
    contact_labels = sorted(
        {c.contact_label for d in days for c in d.contacts_interactions}
    )
    return Baseline(
        mean_screen_time_min=round(mean(d.total_screen_time_min for d in days), 1),
        mean_sleep_hours=round(mean(d.sleep_hours for d in days), 2),
        mean_nighttime_activity_min=round(mean(d.nighttime_activity_min for d in days), 1),
        known_contact_labels=contact_labels,
        app_sessions_per_day={
            app: round(mean(d.sessions_per_app.get(app, 0) for d in days), 1)
            for app in APPS
        },
    )
