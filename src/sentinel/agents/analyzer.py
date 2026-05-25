"""Analyzer agent — detects behavioral risk signals from a MetadataWindow.

Pipeline:
    window → compute_baseline → summarize_window → LLM (with 4 skills) → AnalysisResult
"""
from __future__ import annotations

from typing import ClassVar

from sentinel.agents.base import BaseAgent
from sentinel.config import MODELS
from sentinel.data.models import AnalysisResult, MetadataWindow
from sentinel.tools.baseline import compute_baseline
from sentinel.tools.summary import summarize_window


class Analyzer(BaseAgent):
    name: ClassVar[str] = "analyzer"
    model: ClassVar[str] = MODELS["analyzer"]
    skill_names: ClassVar[list[str]] = [
        "grooming",
        "harassment",
        "addiction",
        "normal_life_event",
    ]

    def run(self, window: MetadataWindow) -> AnalysisResult:
        baseline = compute_baseline(window)
        summary = summarize_window(window, baseline)

        instructions = (
            "You are Sentinel's Analyzer agent. You detect behavioral risk signals "
            "from teen-device METADATA ONLY — never message content (privacy by design).\n\n"
            "Apply the four skills below systematically. Each skill defines named signals "
            "with categories, severities and evidence templates. Use the EXACT signal `name` "
            "keys from the skills (kebab-case identifiers).\n\n"
            "Reason step by step about the data. Cite ACTUAL NUMBERS from the input in "
            "each `evidence` string. Be conservative on `confidence`: a single weak signal "
            "should not exceed 0.5; multiple corroborating signals can justify 0.7-0.9.\n\n"
            "Set `matches_normal_life_event` true ONLY when the deviations are best "
            "explained by exams/holiday/healthy friendship AND no high-severity risk "
            "signal is firing.\n\n"
            "Write `overall_observation` as 2-3 sentences in plain English, suitable for "
            "a non-technical human reviewer (e.g. a parent or a school counselor).\n\n"
            "=== SKILLS ===\n\n"
            f"{self.load_skills()}"
        )

        return self.client.parse(
            instructions=instructions,
            user_input=summary,
            text_format=AnalysisResult,
        )
