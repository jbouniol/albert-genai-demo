"""Pydantic models for synthetic teen behavioral metadata.

Privacy constraint (CLAUDE.md §6): no message content fields. Only counts,
durations, hashed contact IDs, and hour distributions. All models are frozen
so they can flow through LangGraph state immutably (Phase 3).
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AppName = Literal["Discord", "Snapchat", "Instagram", "TikTok", "iMessage"]
ProfileId = Literal["emma", "lucas", "mia"]


class ContactInteraction(BaseModel):
    model_config = ConfigDict(frozen=True)

    contact_id: str
    contact_label: str
    app: AppName
    message_count: int = Field(ge=0)
    avg_response_time_sec: float = Field(ge=0)
    hour_distribution: dict[int, int]


class DailyMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: date
    total_screen_time_min: int = Field(ge=0)
    sessions_per_app: dict[str, int]
    contacts_interactions: list[ContactInteraction]
    nighttime_activity_min: int = Field(ge=0)
    sleep_hours: float = Field(ge=0, le=24)


class MetadataWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: ProfileId
    profile_name: str
    age: int = Field(ge=10, le=18)
    persona_label: str
    days: list[DailyMetadata] = Field(min_length=21, max_length=21)


# ===== Analysis (Phase 2+) =====

SignalCategory = Literal["grooming", "harassment", "addiction", "normal_life_event"]
Severity = Literal["low", "medium", "high"]


class Baseline(BaseModel):
    """Computed from days 0-13 of a MetadataWindow. Internal data, not LLM-facing."""
    model_config = ConfigDict(frozen=True)

    mean_screen_time_min: float
    mean_sleep_hours: float
    mean_nighttime_activity_min: float
    known_contact_labels: list[str]
    app_sessions_per_day: dict[str, float]


class Signal(BaseModel):
    """One behavioral signal detected by the Analyzer."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Signal identifier in kebab-case (e.g. new-contact-escalation).")
    category: SignalCategory
    severity: Severity
    confidence: float = Field(ge=0, le=1, description="0.0 to 1.0 — how sure the model is.")
    evidence: str = Field(
        description="One short factual sentence citing actual numbers from the data."
    )


class AnalysisResult(BaseModel):
    """Structured output of the Analyzer agent."""
    model_config = ConfigDict(frozen=True)

    signals: list[Signal] = Field(
        description="All risk signals detected (can be empty if the profile is RAS)."
    )
    matches_normal_life_event: bool = Field(
        description=(
            "True if the observed deviations are best explained by a normal life event "
            "(exam period, holiday, new healthy friendship) rather than a risk pattern."
        )
    )
    overall_observation: str = Field(
        description="2-3 sentence qualitative read of the profile's behavioral state."
    )


# ===== Scoring (Phase 3+) =====

RiskLevel = Literal["WATCH", "MONITOR", "ALERT", "HIGH_ALERT"]


class ScoreResult(BaseModel):
    """Structured output of the Scorer agent."""
    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0, description="Aggregate risk score from 0 to 1.")
    level: RiskLevel = Field(
        description=(
            "Risk tier: WATCH (<0.30), MONITOR (0.30-0.50), ALERT (0.50-0.65), "
            "HIGH_ALERT (>0.65)."
        )
    )
    rationale: str = Field(
        description=(
            "2-3 sentences explaining the score to a non-technical reviewer "
            "(parent or counselor). Factual, cite the main signals that drove the score."
        )
    )
