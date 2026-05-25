"""Window summarization for LLM consumption.

Produces a compact, structured text summary the Analyzer can reason about
without seeing 21 days of raw JSON. Critical design: surface contact emergence
clearly (a contact that appears mid-window is interesting, even if it's
technically inside the baseline date range).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from sentinel.data.generator import APPS
from sentinel.data.models import Baseline, MetadataWindow

SLIDING_WINDOW = 7
ESTABLISHED_DAYS_THRESHOLD = 14  # contact considered "established" if active ≥N days
PRIMARY_APP_MIN_SHARE = 0.5  # contact has a "primary app" only if ≥50% of msgs there


def _primary_app(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    total = sum(counter.values())
    label, count = counter.most_common(1)[0]
    return label if count / total >= PRIMARY_APP_MIN_SHARE else None


def summarize_window(window: MetadataWindow, baseline: Baseline) -> str:
    """Render a tight textual summary: baseline + last 7 days deltas + per-contact trajectories."""
    days = window.days
    last_7 = days[-SLIDING_WINDOW:]

    # Last-7-day aggregates
    last7_screen = mean(d.total_screen_time_min for d in last_7)
    last7_sleep = mean(d.sleep_hours for d in last_7)
    last7_night = mean(d.nighttime_activity_min for d in last_7)
    last7_apps = {
        app: round(mean(d.sessions_per_app.get(app, 0) for d in last_7), 1) for app in APPS
    }

    # Per-contact aggregates
    contact_first_day: dict[str, int] = {}
    contact_days_active: dict[str, int] = defaultdict(int)
    contact_first7_msgs: dict[str, int] = defaultdict(int)
    contact_last7_msgs: dict[str, int] = defaultdict(int)
    contact_apps_first7: dict[str, Counter[str]] = defaultdict(Counter)
    contact_apps_last7: dict[str, Counter[str]] = defaultdict(Counter)
    contact_resp_first7: dict[str, list[float]] = defaultdict(list)
    contact_resp_last7: dict[str, list[float]] = defaultdict(list)
    contact_last7_hours: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    n_days = len(days)
    for i, d in enumerate(days):
        for c in d.contacts_interactions:
            label = c.contact_label
            if label not in contact_first_day:
                contact_first_day[label] = i
            contact_days_active[label] += 1
            if i < 7:
                contact_first7_msgs[label] += c.message_count
                contact_apps_first7[label][c.app] += c.message_count
                contact_resp_first7[label].append(c.avg_response_time_sec)
            if i >= n_days - 7:
                contact_last7_msgs[label] += c.message_count
                contact_apps_last7[label][c.app] += c.message_count
                contact_resp_last7[label].append(c.avg_response_time_sec)
                for h, n in c.hour_distribution.items():
                    contact_last7_hours[label][h] += n

    # Categorize: established (present from day 0, active most days) vs emerged (first_day > 0)
    established = sorted(
        lbl for lbl in contact_first_day
        if contact_first_day[lbl] == 0
        and contact_days_active[lbl] >= ESTABLISHED_DAYS_THRESHOLD
    )
    emerged = sorted(
        lbl for lbl in contact_first_day if contact_first_day[lbl] > 0
    )

    lines: list[str] = []
    lines.append(f"PROFILE: {window.profile_name}, age {window.age}")
    lines.append(f"Window: 21 days ({days[0].date} → {days[-1].date})")
    lines.append("")

    lines.append("=== BASELINE STATS (days 0-13) ===")
    lines.append(f"- Mean screen time: {baseline.mean_screen_time_min} min/day")
    lines.append(f"- Mean sleep: {baseline.mean_sleep_hours} h")
    lines.append(f"- Mean nighttime activity (22h-6h): {baseline.mean_nighttime_activity_min} min")
    lines.append(
        "- Mean app sessions/day: "
        + ", ".join(f"{a}={v}" for a, v in baseline.app_sessions_per_day.items())
    )
    lines.append("")

    lines.append("=== LAST 7 DAYS (sliding window) ===")
    delta_screen = last7_screen - baseline.mean_screen_time_min
    delta_sleep = last7_sleep - baseline.mean_sleep_hours
    delta_night = last7_night - baseline.mean_nighttime_activity_min
    lines.append(
        f"- Screen time: {last7_screen:.1f} min/day "
        f"(Δ {'+' if delta_screen >= 0 else ''}{delta_screen:.1f})"
    )
    lines.append(
        f"- Sleep: {last7_sleep:.2f} h "
        f"(Δ {'+' if delta_sleep >= 0 else ''}{delta_sleep:.2f})"
    )
    lines.append(
        f"- Nighttime activity: {last7_night:.1f} min "
        f"(Δ {'+' if delta_night >= 0 else ''}{delta_night:.1f})"
    )
    lines.append(
        "- Mean app sessions/day: " + ", ".join(f"{a}={v}" for a, v in last7_apps.items())
    )
    lines.append("")

    def _resp_clause(label: str) -> str:
        first = mean(contact_resp_first7[label]) if contact_resp_first7[label] else None
        last = mean(contact_resp_last7[label]) if contact_resp_last7[label] else None
        if first is not None and last is not None:
            return f", response time first_7d={first:.0f}s → last_7d={last:.0f}s"
        if last is not None:
            return f", response time last_7d={last:.0f}s"
        return ""

    def _peak_clause(label: str) -> str:
        peak_hours = sorted(
            contact_last7_hours[label], key=lambda h: -contact_last7_hours[label][h]
        )[:3]
        return f", peak hours last 7d: {sorted(peak_hours)}" if peak_hours else ""

    def _switch_clause(label: str, is_emerged: bool) -> str:
        primary_first = _primary_app(contact_apps_first7[label])
        primary_last = _primary_app(contact_apps_last7[label])
        if primary_first and primary_last and primary_first != primary_last:
            return f", primary app SWITCHED {primary_first}→{primary_last}"
        if is_emerged and primary_last:
            return f", current primary app={primary_last}"
        if primary_first or primary_last:
            return f", primary app stable (~{primary_first or primary_last})"
        return ""

    lines.append("=== ESTABLISHED CONTACTS (present from day 0, active most days) ===")
    if not established:
        lines.append("- (none)")
    for label in established:
        lines.append(
            f"- {label}: {contact_days_active[label]}/{n_days} days active, "
            f"msgs first_7d={contact_first7_msgs[label]} → last_7d={contact_last7_msgs[label]}"
            f"{_switch_clause(label, is_emerged=False)}"
            f"{_peak_clause(label)}"
            f"{_resp_clause(label)}"
        )
    lines.append("")

    lines.append("=== CONTACTS THAT EMERGED DURING WINDOW (first_day > 0) ===")
    if not emerged:
        lines.append("- (none — no new contact appeared after day 0)")
    for label in emerged:
        first_day = contact_first_day[label]
        lines.append(
            f"- {label}: first appeared day {first_day}, "
            f"{contact_days_active[label]}/{n_days} days active, "
            f"msgs first_7d_of_window={contact_first7_msgs[label]} "
            f"→ last_7d={contact_last7_msgs[label]}"
            f"{_switch_clause(label, is_emerged=True)}"
            f"{_peak_clause(label)}"
            f"{_resp_clause(label)}"
        )

    return "\n".join(lines)
