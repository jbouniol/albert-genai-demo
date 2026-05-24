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
