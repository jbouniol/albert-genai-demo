"""LLM client wrapper — the SOLE entry point for OpenAI calls.

Per CLAUDE.md §5: no agent instantiates OpenAI() directly. Every call passes
through LLMClient so we get consistent logging and auditable chain-of-thought.
"""
from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel

load_dotenv()

_DEFAULT_CONSOLE = Console()


class LLMClient:
    """Unique OpenAI entrypoint. Every agent's LLM call goes through this."""

    def __init__(self, model: str, console: Console | None = None) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY non défini. Copier .env.example vers .env "
                "et y renseigner ta clé OpenAI."
            )
        self.model = model
        self.console = console or _DEFAULT_CONSOLE
        self._client = OpenAI()

    def call(self, instructions: str, user_input: str, **kwargs: Any) -> Any:
        """Call OpenAI Responses API, log input/output, return raw Response.

        Hard constraint (CLAUDE.md §6): logs our agent prompts only. Sentinel
        works on metadata, never on raw message content from end users.
        """
        self._log_input(instructions, user_input)
        start = time.perf_counter()
        response = self._client.responses.create(
            model=self.model,
            instructions=instructions,
            input=user_input,
            **kwargs,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        self._log_output(response, latency_ms)
        return response

    def _log_input(self, instructions: str, user_input: str) -> None:
        body = f"[bold]instructions:[/]\n{instructions}\n\n[bold]input:[/]\n{user_input}"
        self.console.print(
            Panel(body, title=f"INPUT — {self.model}", border_style="cyan", expand=False)
        )

    def _log_output(self, response: Any, latency_ms: int) -> None:
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "input_tokens", "?") if usage else "?"
        out_tok = getattr(usage, "output_tokens", "?") if usage else "?"
        title = f"OUTPUT (latency={latency_ms}ms, tokens={in_tok}/{out_tok})"
        self.console.print(
            Panel(response.output_text, title=title, border_style="green", expand=False)
        )
