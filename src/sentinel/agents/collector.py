"""Collector agent — loads and validates a MetadataWindow from disk.

In production, this agent would aggregate raw data from multiple sources
(iOS Screen Time API, DNS resolver logs, iCloud metadata). In the demo, it
reads the pre-generated profile JSON and validates it via Pydantic.

No LLM call needed here: the data is already structured. The node exists in
the LangGraph graph so the architecture diagram shows all four agents.
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from sentinel.agents.base import BaseAgent
from sentinel.config import MODELS
from sentinel.data.models import MetadataWindow

PROFILES_DIR = Path(__file__).resolve().parents[1] / "data" / "profiles"


class Collector(BaseAgent):
    """Loads and validates a profile JSON → MetadataWindow."""

    name: ClassVar[str] = "collector"
    model: ClassVar[str] = MODELS["collector"]
    skill_names: ClassVar[list[str]] = []

    def run(self, profile_id: str) -> MetadataWindow:  # type: ignore[override]
        """Load profile JSON from disk and validate via Pydantic.

        Args:
            profile_id: One of "emma", "lucas", "mia".

        Returns:
            Validated MetadataWindow (frozen Pydantic model).
        """
        path = PROFILES_DIR / f"{profile_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")
        return MetadataWindow.model_validate_json(path.read_text(encoding="utf-8"))
