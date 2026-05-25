"""BaseAgent — common pattern for all Sentinel agents.

An agent = name + model + skills (markdown files) + a run() method.
All agents share the LLMClient wrapper (CLAUDE.md §5).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from sentinel.llm.client import LLMClient

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


class BaseAgent(ABC):
    name: ClassVar[str]
    model: ClassVar[str]
    skill_names: ClassVar[list[str]] = []

    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client or LLMClient(self.model)

    def load_skills(self) -> str:
        """Concatenate skill markdown files into one prompt section."""
        if not self.skill_names:
            return ""
        chunks: list[str] = []
        for name in self.skill_names:
            path = SKILLS_DIR / f"{name}.md"
            chunks.append(path.read_text(encoding="utf-8"))
        return "\n\n---\n\n".join(chunks)

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent. Subclasses define the concrete signature."""
        ...
