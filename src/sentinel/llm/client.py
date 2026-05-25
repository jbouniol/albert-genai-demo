"""LLM client wrapper — the SOLE entry point for OpenAI calls.

Per CLAUDE.md §5: no agent instantiates OpenAI() directly. Every call passes
through LLMClient so we get consistent logging and auditable chain-of-thought.

Phase 4+5 additions:
- `stream_call()` for token-level streaming (Communicator's parent notification)
- `SentinelLLMError` typed errors (timeout / ratelimit / quota / unknown)
- Quiet mode via SENTINEL_QUIET=1 (used by Streamlit demo to clean terminal)
"""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any, Literal, TypeVar

import openai
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

load_dotenv()

_QUIET = os.getenv("SENTINEL_QUIET") == "1"
_DEFAULT_CONSOLE = Console(quiet=_QUIET)

T = TypeVar("T", bound=BaseModel)

ErrorKind = Literal["timeout", "ratelimit", "quota", "unknown"]


class SentinelLLMError(RuntimeError):
    """Typed wrapper around OpenAI errors so the UI can react appropriately."""

    def __init__(self, kind: ErrorKind, original: Exception) -> None:
        self.kind = kind
        self.original = original
        super().__init__(f"{kind}: {original}")


def _classify_openai_error(err: Exception) -> ErrorKind:
    if isinstance(err, openai.APITimeoutError):
        return "timeout"
    if isinstance(err, openai.RateLimitError):
        return "quota" if "insufficient_quota" in str(err) else "ratelimit"
    if isinstance(err, openai.APIError):
        return "unknown"
    return "unknown"


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

    # ------------------------------------------------------------------ public

    def call(self, instructions: str, user_input: str, **kwargs: Any) -> Any:
        """Call OpenAI Responses API, log input/output, return raw Response.

        Hard constraint (CLAUDE.md §6): logs our agent prompts only. Sentinel
        works on metadata, never on raw message content from end users.
        """
        self._log_input(instructions, user_input)
        start = time.perf_counter()
        response = self._safe(
            lambda: self._client.responses.create(
                model=self.model,
                instructions=instructions,
                input=user_input,
                **kwargs,
            )
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        self._log_output(response, latency_ms)
        return response

    def parse(
        self,
        instructions: str,
        user_input: str,
        text_format: type[T],
        **kwargs: Any,
    ) -> T:
        """Structured output via Pydantic. Returns the parsed model instance.

        Wraps client.responses.parse — same logging contract as call().
        """
        self._log_input(instructions, user_input)
        start = time.perf_counter()
        response = self._safe(
            lambda: self._client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=user_input,
                text_format=text_format,
                **kwargs,
            )
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        self._log_output(response, latency_ms)
        if response.output_parsed is None:
            raise RuntimeError(
                f"responses.parse returned no parsed output for "
                f"{text_format.__name__}. Raw: {response.output_text!r}"
            )
        return response.output_parsed

    def stream_call(
        self,
        instructions: str,
        user_input: str,
        on_delta: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> str:
        """Stream a plain-text response token-by-token.

        Calls `on_delta(chunk)` for each incremental text delta. Returns the
        full concatenated output text. Used by the Communicator agent to
        render its parent notification with a typing effect in Streamlit.

        Hard fallback: if `responses.stream()` event types differ from the
        expected `response.output_text.delta`, we iterate `stream.text_stream`
        which is a SDK-provided string iterator.
        """
        self._log_input(instructions, user_input)
        start = time.perf_counter()
        chunks: list[str] = []

        def _do_stream() -> Any:
            with self._client.responses.stream(
                model=self.model,
                instructions=instructions,
                input=user_input,
                **kwargs,
            ) as stream:
                got_event = False
                for event in stream:
                    # Modern SDK path
                    etype = getattr(event, "type", "")
                    if etype == "response.output_text.delta":
                        got_event = True
                        delta = getattr(event, "delta", "")
                        if delta:
                            chunks.append(delta)
                            if on_delta:
                                on_delta(delta)
                # SDK fallback: iterate text_stream if the event loop yielded nothing useful
                if not got_event:
                    for piece in stream.text_stream:  # type: ignore[attr-defined]
                        if piece:
                            chunks.append(piece)
                            if on_delta:
                                on_delta(piece)
                return stream.get_final_response()

        final = self._safe(_do_stream)
        latency_ms = int((time.perf_counter() - start) * 1000)
        self._log_output(final, latency_ms)
        text = "".join(chunks) or getattr(final, "output_text", "")
        return text

    # ------------------------------------------------------------------ private

    def _safe(self, fn: Callable[[], Any]) -> Any:
        """Run the OpenAI call, classify errors into SentinelLLMError."""
        try:
            return fn()
        except SentinelLLMError:
            raise
        except Exception as e:  # noqa: BLE001 — classify, then re-raise typed
            raise SentinelLLMError(_classify_openai_error(e), e) from e

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
            Panel(
                getattr(response, "output_text", ""),
                title=title,
                border_style="green",
                expand=False,
            )
        )
