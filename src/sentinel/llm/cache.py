"""CachedLLMClient — disk-backed replay of LLM outputs.

Why subclass `LLMClient` rather than add a flag inside it:
- keeps the real client free of cache concerns,
- exploits the seam `BaseAgent.__init__(client=None)` already exposes,
- agents stay branch-free (no `if cached:` inside them).

Cache key = (agent_name, profile_id). NOT prompt hash — the demo only ever runs
3 fixed profiles, and prompt-hash caching is YAGNI here.

Files:
    data/llm_cache/<profile_id>/<agent_name>.json   (for parse() outputs)
    data/llm_cache/<profile_id>/<agent_name>.txt    (for call() / stream_call())

The cached `stream_call()` replays the saved text char-by-char with a small
sleep so the jury sees the typing effect even in backup mode.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel
from rich.console import Console

from sentinel.llm.client import LLMClient

T = TypeVar("T", bound=BaseModel)

# data/llm_cache/ lives at the repo root, two levels up from this file:
#   src/sentinel/llm/cache.py → parents[3] = repo root
CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "llm_cache"

# Pacing for the cached typing effect: 5ms/char ≈ 2.5s for a ~500-char notif.
CACHED_TYPING_DELAY_SEC = 0.005


class CachedLLMClient(LLMClient):
    """LLMClient that reads from / writes to disk per (profile_id, agent_name).

    On cache hit: returns the persisted result instantly (no API call).
    On cache miss: delegates to the parent LLMClient, then persists the output.
    """

    def __init__(
        self,
        model: str,
        agent_name: str,
        profile_id: str,
        cache_dir: Path = CACHE_DIR,
        console: Console | None = None,
    ) -> None:
        super().__init__(model=model, console=console)
        self._agent_name = agent_name
        self._profile_id = profile_id
        self._dir = cache_dir / profile_id

    # ---------------------------------------------------------------- helpers

    @property
    def _json_path(self) -> Path:
        return self._dir / f"{self._agent_name}.json"

    @property
    def _text_path(self) -> Path:
        return self._dir / f"{self._agent_name}.txt"

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- API

    def parse(
        self,
        instructions: str,
        user_input: str,
        text_format: type[T],
        **kwargs: Any,
    ) -> T:
        path = self._json_path
        if path.exists():
            return text_format.model_validate_json(path.read_text(encoding="utf-8"))
        result = super().parse(instructions, user_input, text_format, **kwargs)
        self._ensure_dir()
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    def call(self, instructions: str, user_input: str, **kwargs: Any) -> Any:
        path = self._text_path
        if path.exists():
            return _CachedResponse(path.read_text(encoding="utf-8"))
        response = super().call(instructions, user_input, **kwargs)
        self._ensure_dir()
        path.write_text(response.output_text, encoding="utf-8")
        return response

    def stream_call(
        self,
        instructions: str,
        user_input: str,
        on_delta: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> str:
        path = self._text_path
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if on_delta:
                for ch in text:
                    on_delta(ch)
                    time.sleep(CACHED_TYPING_DELAY_SEC)
            return text
        text = super().stream_call(instructions, user_input, on_delta=on_delta, **kwargs)
        self._ensure_dir()
        path.write_text(text, encoding="utf-8")
        return text


class _CachedResponse:
    """Minimal stand-in for an OpenAI Response — just exposes `.output_text`."""

    __slots__ = ("output_text",)

    def __init__(self, text: str) -> None:
        self.output_text = text
