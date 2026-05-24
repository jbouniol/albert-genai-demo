"""Synthetic data generator for the 3 demo profiles.

Deterministic: each profile uses a fixed seed → identical JSON output every run.
The downstream agent (Phase 2+) remains non-deterministic (LLM), so the demo
score still varies, but the input data is stable.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Final

from sentinel.data.models import (
    AppName,
    ContactInteraction,
    DailyMetadata,
    MetadataWindow,
)

WINDOW_START: Final[date] = date(2026, 5, 3)
WINDOW_DAYS: Final[int] = 21
APPS: Final[tuple[AppName, ...]] = (
    "Discord",
    "Snapchat",
    "Instagram",
    "TikTok",
    "iMessage",
)
SEEDS: Final[dict[str, int]] = {"emma": 42, "lucas": 1337, "mia": 7919}


def _dates() -> list[date]:
    return [WINDOW_START + timedelta(days=i) for i in range(WINDOW_DAYS)]


def _hash_contact(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:12]


def _peak_hours(start: int, end: int) -> list[int]:
    """Hours in [start, end], handling midnight wrap (e.g. 23 → 2 = [23, 0, 1, 2])."""
    if start <= end:
        return list(range(start, end + 1))
    return list(range(start, 24)) + list(range(0, end + 1))


def _distribute_hours(
    rng: random.Random,
    total_msgs: int,
    peak_start: int,
    peak_end: int,
) -> dict[int, int]:
    """Spread total_msgs across 24h: ~70% in [peak_start, peak_end], rest 8h-22h."""
    if total_msgs == 0:
        return {}
    dist: dict[int, int] = {}
    peak_hours = _peak_hours(peak_start, peak_end)
    peak_set = set(peak_hours)
    peak_msgs = int(total_msgs * 0.7)
    other_msgs = total_msgs - peak_msgs
    for _ in range(peak_msgs):
        h = rng.choice(peak_hours)
        dist[h] = dist.get(h, 0) + 1
    non_peak = [h for h in range(8, 23) if h not in peak_set]
    if not non_peak:
        non_peak = list(range(8, 23))
    for _ in range(other_msgs):
        h = rng.choice(non_peak)
        dist[h] = dist.get(h, 0) + 1
    return dist


# ---------- EMMA — baseline stable + exam period ----------

def generate_emma_profile() -> MetadataWindow:
    rng = random.Random(SEEDS["emma"])
    friends = [f"Friend_{i}" for i in range(1, 6)]
    days: list[DailyMetadata] = []

    for day_idx, d in enumerate(_dates()):
        is_exam = 14 <= day_idx <= 17

        base_screen = rng.normalvariate(120, 18)
        if is_exam:
            base_screen *= 1.40
        screen_time = max(60, int(base_screen))

        base_sleep = rng.normalvariate(8.0, 0.35)
        if is_exam:
            base_sleep -= 1.0
        sleep = max(5.0, min(10.0, base_sleep))

        sessions = {
            "Instagram": rng.randint(8, 12),
            "iMessage": rng.randint(10, 14),
            "Discord": rng.randint(8, 14) if is_exam else rng.randint(3, 6),
            "TikTok": rng.randint(6, 10),
            "Snapchat": rng.randint(3, 5),
        }

        contacts: list[ContactInteraction] = []
        for friend in friends:
            n_msgs = rng.randint(8, 15)
            app: AppName = rng.choice(["Instagram", "iMessage"])
            contacts.append(
                ContactInteraction(
                    contact_id=_hash_contact(friend),
                    contact_label=friend,
                    app=app,
                    message_count=n_msgs,
                    avg_response_time_sec=round(rng.uniform(60, 600), 1),
                    hour_distribution=_distribute_hours(rng, n_msgs, 17, 21),
                )
            )

        nighttime = rng.randint(15, 35) if is_exam else rng.randint(5, 20)

        days.append(
            DailyMetadata(
                date=d,
                total_screen_time_min=screen_time,
                sessions_per_app=sessions,
                contacts_interactions=contacts,
                nighttime_activity_min=nighttime,
                sleep_hours=round(sleep, 2),
            )
        )

    return MetadataWindow(
        profile_id="emma",
        profile_name="Emma",
        age=14,
        persona_label="Normal teen baseline (exam period mid-window)",
        days=days,
    )


# ---------- LUCAS — progressive grooming ----------

def generate_lucas_profile() -> MetadataWindow:
    rng = random.Random(SEEDS["lucas"])
    friends = [f"Friend_{i}" for i in range(1, 6)]
    days: list[DailyMetadata] = []

    for day_idx, d in enumerate(_dates()):
        # Jake_M_15 pattern: absent → Discord → Snapchat, escalating frequency + hours
        if day_idx < 2:
            jake_msgs, jake_app, jake_peak = 0, None, None
        elif day_idx < 7:
            jake_msgs = rng.randint(5, 10)
            jake_app, jake_peak = "Discord", (18, 22)
        elif day_idx < 10:
            jake_msgs = rng.randint(20, 35)
            jake_app, jake_peak = "Discord", (19, 23)
        elif day_idx < 14:
            jake_msgs = rng.randint(40, 60)
            jake_app, jake_peak = "Snapchat", (21, 0)
        elif day_idx < 18:
            jake_msgs = rng.randint(60, 85)
            jake_app, jake_peak = "Snapchat", (22, 1)
        else:
            jake_msgs = rng.randint(80, 110)
            jake_app, jake_peak = "Snapchat", (23, 2)

        # Baseline friends: progressive drop (30 → 12)
        drop_factor = max(0.4, 1.0 - day_idx * 0.03)
        baseline_total = max(5, int(30 * drop_factor))
        per_friend = max(1, baseline_total // 5)

        contacts: list[ContactInteraction] = []

        if jake_msgs > 0 and jake_app is not None and jake_peak is not None:
            jake_hours = _distribute_hours(rng, jake_msgs, *jake_peak)
            contacts.append(
                ContactInteraction(
                    contact_id=_hash_contact("Jake_M_15"),
                    contact_label="Jake_M_15",
                    app=jake_app,
                    message_count=jake_msgs,
                    avg_response_time_sec=round(rng.uniform(30, 180), 1),
                    hour_distribution=jake_hours,
                )
            )

        for friend in friends:
            n_msgs = max(1, per_friend + rng.randint(-2, 2))
            app: AppName = rng.choice(["Instagram", "iMessage", "Discord"])
            contacts.append(
                ContactInteraction(
                    contact_id=_hash_contact(friend),
                    contact_label=friend,
                    app=app,
                    message_count=n_msgs,
                    avg_response_time_sec=round(rng.uniform(120, 900), 1),
                    hour_distribution=_distribute_hours(rng, n_msgs, 17, 21),
                )
            )

        # Screen time ramps 130 → 210
        screen_time = max(60, int(130 + day_idx * 4 + rng.normalvariate(0, 10)))

        # Sleep declines 8 → 6
        sleep = max(5.5, 8.0 - day_idx * 0.1 + rng.normalvariate(0, 0.25))

        # Nighttime activity ramps 5 → ~90
        nighttime = max(0, int(5 + day_idx * 4.5 + rng.normalvariate(0, 4)))

        # Sessions: Discord dominant → Snapchat takes over
        if day_idx < 10:
            sessions = {
                "Discord": rng.randint(12, 18),
                "Snapchat": rng.randint(4, 8),
                "Instagram": rng.randint(8, 12),
                "TikTok": rng.randint(6, 10),
                "iMessage": rng.randint(8, 12),
            }
        else:
            sessions = {
                "Discord": rng.randint(4, 8),
                "Snapchat": rng.randint(15, 25),
                "Instagram": rng.randint(6, 10),
                "TikTok": rng.randint(5, 8),
                "iMessage": rng.randint(6, 10),
            }

        days.append(
            DailyMetadata(
                date=d,
                total_screen_time_min=screen_time,
                sessions_per_app=sessions,
                contacts_interactions=contacts,
                nighttime_activity_min=nighttime,
                sleep_hours=round(sleep, 2),
            )
        )

    return MetadataWindow(
        profile_id="lucas",
        profile_name="Lucas",
        age=15,
        persona_label="Potential grooming victim (new adult-coded contact)",
        days=days,
    )


# ---------- MIA — harassment by known contact ----------

def generate_mia_profile() -> MetadataWindow:
    rng = random.Random(SEEDS["mia"])
    friends = [f"Friend_{i}" for i in range(1, 5)]  # 4 friends — slightly smaller circle
    days: list[DailyMetadata] = []

    for day_idx, d in enumerate(_dates()):
        # Alex_K (known classmate): baseline → harassment spike at day 10
        if day_idx < 10:
            alex_msgs = rng.randint(5, 10)
            alex_peak = (16, 20)
            alex_resp = round(rng.uniform(60, 240), 1)
        elif day_idx < 15:
            alex_msgs = rng.randint(40, 60)
            alex_peak = (14, 23)
            alex_resp = round(rng.uniform(600, 1500), 1)
        else:
            alex_msgs = rng.randint(45, 65)
            alex_peak = (14, 23)
            alex_resp = round(rng.uniform(900, 1800), 1)

        contacts: list[ContactInteraction] = [
            ContactInteraction(
                contact_id=_hash_contact("Alex_K"),
                contact_label="Alex_K",
                app="iMessage",
                message_count=alex_msgs,
                avg_response_time_sec=alex_resp,
                hour_distribution=_distribute_hours(rng, alex_msgs, *alex_peak),
            )
        ]

        for friend in friends:
            n_msgs = rng.randint(5, 12)
            app: AppName = rng.choice(["Instagram", "iMessage"])
            contacts.append(
                ContactInteraction(
                    contact_id=_hash_contact(friend),
                    contact_label=friend,
                    app=app,
                    message_count=n_msgs,
                    avg_response_time_sec=round(rng.uniform(120, 600), 1),
                    hour_distribution=_distribute_hours(rng, n_msgs, 16, 20),
                )
            )

        # Sleep: stable 8h then decline 7 → 5.5
        if day_idx < 10:
            sleep = rng.normalvariate(8.0, 0.3)
        else:
            t = (day_idx - 10) / 10
            target = 7.0 - 1.5 * t
            sleep = target + rng.normalvariate(0, 0.25)
        sleep = max(4.5, min(10.0, sleep))

        # TikTok withdrawal after day 10
        tiktok_sessions = rng.randint(10, 15) if day_idx < 10 else rng.randint(3, 6)

        sessions = {
            "iMessage": rng.randint(10, 15),
            "Instagram": rng.randint(6, 10),
            "TikTok": tiktok_sessions,
            "Snapchat": rng.randint(2, 5),
            "Discord": rng.randint(1, 3),
        }

        # Slight screen time withdrawal in last week
        if day_idx < 14:
            screen_time = max(60, int(rng.normalvariate(130, 15)))
        else:
            screen_time = max(60, int(rng.normalvariate(108, 15)))

        # Nighttime insomnia after day 10
        if day_idx < 10:
            nighttime = rng.randint(5, 15)
        else:
            nighttime = rng.randint(20, 45)

        days.append(
            DailyMetadata(
                date=d,
                total_screen_time_min=screen_time,
                sessions_per_app=sessions,
                contacts_interactions=contacts,
                nighttime_activity_min=nighttime,
                sleep_hours=round(sleep, 2),
            )
        )

    return MetadataWindow(
        profile_id="mia",
        profile_name="Mia",
        age=13,
        persona_label="Potential harassment victim (known contact pattern)",
        days=days,
    )
