"""Tests for synthetic data generators.

Verifies each profile carries its signature pattern (CLAUDE.md §9):
    - Lucas: grooming (new contact escalation, nocturnal drift, app switch, friends drop)
    - Mia: harassment (known contact spike, sleep collapse, social withdrawal)
    - Emma: stable baseline with exam-period spike (anti-false-positive)
"""
from __future__ import annotations

import statistics
from datetime import timedelta

import pytest

from sentinel.data.generator import (
    WINDOW_DAYS,
    WINDOW_START,
    generate_emma_profile,
    generate_lucas_profile,
    generate_mia_profile,
)
from sentinel.data.models import MetadataWindow


@pytest.fixture(scope="module")
def emma() -> MetadataWindow:
    return generate_emma_profile()


@pytest.fixture(scope="module")
def lucas() -> MetadataWindow:
    return generate_lucas_profile()


@pytest.fixture(scope="module")
def mia() -> MetadataWindow:
    return generate_mia_profile()


# ===== COMMON: shape, validity, determinism =====

ALL_GENERATORS = [generate_emma_profile, generate_lucas_profile, generate_mia_profile]


@pytest.mark.parametrize("gen", ALL_GENERATORS)
def test_window_length_is_21(gen):
    assert len(gen().days) == WINDOW_DAYS == 21


@pytest.mark.parametrize("gen", ALL_GENERATORS)
def test_dates_are_contiguous(gen):
    p = gen()
    assert p.days[0].date == WINDOW_START
    for i in range(1, 21):
        assert p.days[i].date == p.days[i - 1].date + timedelta(days=1)


@pytest.mark.parametrize("gen", ALL_GENERATORS)
def test_screen_time_in_sane_range(gen):
    for day in gen().days:
        assert 30 <= day.total_screen_time_min <= 480


@pytest.mark.parametrize("gen", ALL_GENERATORS)
def test_deterministic(gen):
    a = gen().model_dump_json()
    b = gen().model_dump_json()
    assert a == b, "generator is not deterministic — check random.Random(seed) usage"


# ===== LUCAS — grooming signature =====

def _contact_msgs(profile: MetadataWindow, day_idx: int, label: str) -> int:
    for c in profile.days[day_idx].contacts_interactions:
        if c.contact_label == label:
            return c.message_count
    return 0


def _contact_app(profile: MetadataWindow, day_idx: int, label: str) -> str | None:
    for c in profile.days[day_idx].contacts_interactions:
        if c.contact_label == label:
            return c.app
    return None


class TestLucasGrooming:
    def test_jake_absent_then_present(self, lucas):
        for i in range(2):
            assert _contact_msgs(lucas, i, "Jake_M_15") == 0, f"day {i}: Jake should be absent"
        for i in range(2, 21):
            assert _contact_msgs(lucas, i, "Jake_M_15") > 0, f"day {i}: Jake should be present"

    def test_jake_messages_escalate(self, lucas):
        first_week = sum(_contact_msgs(lucas, i, "Jake_M_15") for i in range(2, 9))
        last_week = sum(_contact_msgs(lucas, i, "Jake_M_15") for i in range(14, 21))
        assert last_week > 5 * first_week, (
            f"escalation too weak: first_week={first_week}, last_week={last_week}"
        )

    def test_nocturnal_activity_doubles(self, lucas):
        first_7 = statistics.mean(d.nighttime_activity_min for d in lucas.days[:7])
        last_7 = statistics.mean(d.nighttime_activity_min for d in lucas.days[-7:])
        assert last_7 > 2 * first_7, f"nocturnal first={first_7:.1f}, last={last_7:.1f}"

    def test_jake_app_switch_discord_to_snapchat(self, lucas):
        for i in range(2, 10):
            assert _contact_app(lucas, i, "Jake_M_15") == "Discord", f"day {i}: expected Discord"
        for i in range(10, 21):
            assert _contact_app(lucas, i, "Jake_M_15") == "Snapchat", (
                f"day {i}: expected Snapchat"
            )

    def test_baseline_friends_drop(self, lucas):
        def friends_total(start: int, end: int) -> int:
            return sum(
                c.message_count
                for d in lucas.days[start:end]
                for c in d.contacts_interactions
                if c.contact_label.startswith("Friend_")
            )
        first_7 = friends_total(0, 7)
        last_7 = friends_total(14, 21)
        assert last_7 < 0.6 * first_7, f"friends drop too weak: first={first_7}, last={last_7}"


# ===== MIA — harassment signature =====

class TestMiaHarassment:
    def test_alex_always_present(self, mia):
        for i in range(21):
            assert _contact_msgs(mia, i, "Alex_K") >= 5, f"day {i}: Alex missing or too quiet"

    def test_alex_spike_from_day_10(self, mia):
        peak_days = sum(1 for i in range(10, 21) if _contact_msgs(mia, i, "Alex_K") >= 40)
        assert peak_days >= 7, f"only {peak_days} days at ≥40 msgs, need ≥7"

    def test_sleep_collapses_after_day_10(self, mia):
        late_sleep = statistics.mean(d.sleep_hours for d in mia.days[10:])
        assert late_sleep < 6.5, f"sleep after day 10 mean = {late_sleep:.2f}"

    def test_tiktok_withdrawal(self, mia):
        first_7 = sum(d.sessions_per_app.get("TikTok", 0) for d in mia.days[:7])
        last_8 = sum(d.sessions_per_app.get("TikTok", 0) for d in mia.days[13:21])
        assert last_8 < 0.5 * first_7, f"TikTok first_7={first_7}, last_8={last_8}"

    def test_no_new_suspicious_contact(self, mia):
        first_week_ids = {c.contact_id for d in mia.days[:7] for c in d.contacts_interactions}
        last_week_ids = {c.contact_id for d in mia.days[14:] for c in d.contacts_interactions}
        assert last_week_ids.issubset(first_week_ids), (
            "Mia should have no new contacts (signature differs from Lucas grooming)"
        )


# ===== EMMA — stable baseline with exam spike =====

class TestEmmaNormal:
    def test_screen_time_stable_outside_exams(self, emma):
        non_exam_days = emma.days[:14] + emma.days[18:]
        values = [d.total_screen_time_min for d in non_exam_days]
        assert statistics.stdev(values) < 40, f"non-exam stdev = {statistics.stdev(values):.1f}"

    def test_exam_period_spike(self, emma):
        exam_mean = statistics.mean(d.total_screen_time_min for d in emma.days[14:18])
        baseline_mean = statistics.mean(
            d.total_screen_time_min for d in emma.days[:14] + emma.days[18:]
        )
        assert exam_mean > 1.25 * baseline_mean, (
            f"exam_mean={exam_mean:.1f}, baseline_mean={baseline_mean:.1f}"
        )

    def test_no_unknown_contacts(self, emma):
        labels = {c.contact_label for d in emma.days for c in d.contacts_interactions}
        assert all(label.startswith("Friend_") for label in labels), labels

    def test_decent_average_sleep(self, emma):
        avg_sleep = statistics.mean(d.sleep_hours for d in emma.days)
        assert avg_sleep >= 7.5, f"avg_sleep={avg_sleep:.2f}"
