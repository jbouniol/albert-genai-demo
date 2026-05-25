"""Scorer agent — aggregates Analyzer signals into a 0-1 risk score.

Pipeline:
    AnalysisResult (signals + flags) → LLM (gpt-4o) → ScoreResult (score + level + rationale)
"""
from __future__ import annotations

from typing import ClassVar

from sentinel.agents.base import BaseAgent
from sentinel.config import MODELS, THRESHOLDS
from sentinel.data.models import AnalysisResult, MetadataWindow, ScoreResult


def _format_analysis_for_scorer(window: MetadataWindow, analysis: AnalysisResult) -> str:
    """Render AnalysisResult as clean text for the Scorer LLM."""
    lines: list[str] = []
    lines.append(f"PROFILE: {window.profile_name}, age {window.age}")
    lines.append(f"matches_normal_life_event: {analysis.matches_normal_life_event}")
    lines.append(f"overall_observation: {analysis.overall_observation}")
    lines.append("")

    if analysis.signals:
        lines.append(f"SIGNALS DETECTED ({len(analysis.signals)}):")
        for s in analysis.signals:
            lines.append(
                f"  [{s.severity.upper()} | {s.category} | conf={s.confidence:.2f}] "
                f"{s.name}: {s.evidence}"
            )
    else:
        lines.append("SIGNALS DETECTED: none")

    return "\n".join(lines)


class Scorer(BaseAgent):
    """Aggregates risk signals into a calibrated 0-1 score with an actionable tier."""

    name: ClassVar[str] = "scorer"
    model: ClassVar[str] = MODELS["scorer"]
    skill_names: ClassVar[list[str]] = []

    def run(  # type: ignore[override]
        self, window: MetadataWindow, analysis: AnalysisResult
    ) -> ScoreResult:
        """Score the behavioral risk level from Analyzer output.

        Args:
            window: The profile's MetadataWindow (for name/age context).
            analysis: Structured signals + flags from the Analyzer agent.

        Returns:
            ScoreResult with a calibrated 0-1 score, level tier, and rationale.
        """
        instructions = (
            "You are Sentinel's Scorer agent. Your job is to produce a calibrated "
            "behavioral risk score (0.0–1.0) from the signals the Analyzer detected.\n\n"
            "=== SCORING RUBRIC ===\n\n"
            f"WATCH      score < {THRESHOLDS['watch']:.2f}  — No or weak signals. "
            "Normal behavior, possibly a transient variation.\n"
            f"MONITOR    score {THRESHOLDS['watch']:.2f}–{THRESHOLDS['monitor']:.2f}   — "
            "Some signals, low severity, no clear pattern. Keep an eye.\n"
            f"ALERT      score {THRESHOLDS['monitor']:.2f}–{THRESHOLDS['alert']:.2f}   — "
            "Moderate signals with some corroboration. Parent conversation recommended.\n"
            f"HIGH_ALERT score > {THRESHOLDS['high_alert']:.2f}  — "
            "Strong, corroborated high-severity signals. Immediate attention warranted.\n\n"
            "=== CALIBRATION RULES ===\n\n"
            "1. `matches_normal_life_event=True` caps the score at 0.38 UNLESS a HIGH "
            "severity risk signal is also present (exams don't explain grooming).\n"
            "2. A single low-confidence signal alone should not exceed 0.45.\n"
            "3. Multiple HIGH severity signals with confidence ≥0.7 should produce ≥0.72.\n"
            "4. Corroboration compounds: three medium signals are more alarming than one high.\n"
            "5. An empty signals list → score ≤ 0.20.\n\n"
            "=== OUTPUT RULES ===\n\n"
            "- `score`: precise float, e.g. 0.78, not 0.8 or 0.80.\n"
            "- `level`: one of WATCH / MONITOR / ALERT / HIGH_ALERT, consistent with score.\n"
            "- `rationale`: 2-3 sentences, factual, plain English for a parent or school "
            "counselor. Cite actual signal names and confidence values. No jargon."
        )

        user_input = _format_analysis_for_scorer(window, analysis)
        return self.client.parse(
            instructions=instructions,
            user_input=user_input,
            text_format=ScoreResult,
        )
