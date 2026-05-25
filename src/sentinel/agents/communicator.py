"""Communicator agent — drafts the parent notification when score > HITL_TRIGGER.

Pipeline:
    MetadataWindow + ScoreResult → LLM (gpt-4o-mini) → notification message (str)

Triggered ONLY when score > 0.65 (HITL_TRIGGER). The output is a short, factual,
non-alarmist message a parent would receive via the Sentinel app.

Phase 4: supports an optional `on_text_delta` callback for token-level streaming
(used by the Streamlit demo to render the notification with a typing effect).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from sentinel.agents.base import BaseAgent
from sentinel.config import MODELS
from sentinel.data.models import MetadataWindow, ScoreResult


def _format_input(window: MetadataWindow, score_result: ScoreResult) -> str:
    lines: list[str] = [
        f"Child name: {window.profile_name}",
        f"Child age: {window.age}",
        f"Risk score: {score_result.score:.2f} ({score_result.level})",
        f"Scorer rationale: {score_result.rationale}",
    ]
    return "\n".join(lines)


class Communicator(BaseAgent):
    """Drafts a parent notification from the ScoreResult.

    Only called by the LangGraph orchestrator when score > HITL_TRIGGER (0.65).
    """

    name: ClassVar[str] = "communicator"
    model: ClassVar[str] = MODELS["communicator"]
    skill_names: ClassVar[list[str]] = []

    def run(  # type: ignore[override]
        self,
        window: MetadataWindow,
        score_result: ScoreResult,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> str:
        """Draft the parent notification message.

        Args:
            window: Profile metadata (name, age).
            score_result: Risk score and rationale from the Scorer.
            on_text_delta: Optional callback receiving each text chunk as the
                LLM streams. When provided, uses `client.stream_call()` for
                token-level streaming; otherwise falls back to a single
                synchronous `client.call()`.

        Returns:
            Plain-text notification message for the parent.
        """
        instructions = (
            "You are Sentinel's Communicator agent. You write short, clear, "
            "non-alarmist notification messages for parents about their child's "
            "digital behavior. The message is sent via the Sentinel mobile app.\n\n"
            "=== MESSAGE RULES ===\n\n"
            "1. NEVER reveal message content — Sentinel only analyzes metadata "
            "(frequency, timing, app usage). Say so explicitly.\n"
            "2. Keep it SHORT: 3-4 sentences max in the body. No walls of text.\n"
            "3. Tone: warm, factual, reassuring. NOT alarming. NOT diagnostic. "
            "Parents should feel informed, not panicked.\n"
            "4. ALWAYS end with a gentle call-to-action: suggest a calm, open "
            "conversation with the child.\n"
            "5. Do NOT name specific contacts or reveal the child's private "
            "communications — metadata only.\n"
            "6. Format: start with a one-line subject, then the message body.\n\n"
            "Example structure:\n"
            "Subject: A pattern in [name]'s device activity worth a conversation\n\n"
            "Hi,\n\n"
            "[2-3 sentence factual observation about behavioral patterns — "
            "e.g. timing, app changes, contact frequency changes — without content.]\n\n"
            "We suggest having a calm, open conversation with [name] about their "
            "online interactions. This is not an emergency — early awareness helps.\n\n"
            "— Sentinel Safety"
        )

        user_input = _format_input(window, score_result)
        if on_text_delta is not None:
            return self.client.stream_call(
                instructions=instructions,
                user_input=user_input,
                on_delta=on_text_delta,
            )
        response = self.client.call(instructions=instructions, user_input=user_input)
        return response.output_text
